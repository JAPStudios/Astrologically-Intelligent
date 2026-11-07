"""Minimal authenticated JSON HTTP API for chat and agent control."""
from __future__ import annotations

import hmac
import json
import math
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from .runtime import AgentRuntime, _valid_session_id
from .orchestration import AGENT_STATES, APPROVAL_STATES

_RESOURCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_DECISIONS = {"approved", "rejected", "cancelled"}


def _valid_resource_id(value: object) -> bool:
    return isinstance(value, str) and bool(_RESOURCE_ID.fullmatch(value))


def _finite_nonnegative(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value)) and value >= 0
    except (OverflowError, ValueError):
        return False


_SENSITIVE_CONFIG_KEY = re.compile(
    r"(?:api[_-]?key|token|secret|password|credential|authorization|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)


def _safe_agent(agent: dict | None):
    if agent is None:
        return None
    result = dict(agent)
    raw_config = result.get("config", {})
    try:
        config = json.loads(raw_config) if isinstance(raw_config, str) else raw_config
    except (TypeError, ValueError):
        config = {}

    def redact(value):
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if _SENSITIVE_CONFIG_KEY.search(str(key)) else redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    result["config"] = redact(config)
    return result

def make_handler(runtime: AgentRuntime, token: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            return not token or hmac.compare_digest(
                self.headers.get("Authorization", ""), f"Bearer {token}"
            )

        def _control_authorized(self):
            return bool(token) and self._authorized()

        def _read_object(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except (TypeError, ValueError):
                self._send(400, {"error": "invalid_content_length"})
                return None
            if length < 1 or length > 1_000_000:
                self._send(413, {"error": "invalid_body_size"})
                return None
            try:
                payload = json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, {"error": "invalid_json"})
                return None
            if not isinstance(payload, dict):
                self._send(400, {"error": "body_must_be_object"})
                return None
            return payload

        @staticmethod
        def _text(payload, key, maximum, *, required=True):
            value = payload.get(key)
            if value is None and not required:
                return ""
            if not isinstance(value, str):
                return None
            value = value.strip()
            if (required and not value) or len(value) > maximum:
                return None
            return value

        def do_GET(self):
            parsed = urlsplit(self.path)
            path = parsed.path
            if path == "/health":
                return self._send(200, {"status": "ok", "service": "astrologically-intelligent"})
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            control_route = (
                path.startswith(("/v1/agents", "/v1/goals", "/v1/approvals",
                                 "/v1/budgets", "/v1/runs"))
            )
            if control_route and not self._control_authorized():
                return self._send(401, {"error": "control_plane_authentication_required"})
            query = parse_qs(parsed.query, keep_blank_values=True)
            orchestration = runtime.tools.orchestration

            if path == "/v1/sessions":
                try:
                    limit = int(query.get("limit", ["50"])[0])
                except (TypeError, ValueError):
                    return self._send(400, {"error": "invalid_limit"})
                if not 1 <= limit <= 100:
                    return self._send(400, {"error": "invalid_limit"})
                return self._send(200, {"sessions": runtime.store.list_sessions(limit)})

            if path == "/v1/history":
                session_id = query.get("session_id", [""])[0]
                if not _valid_session_id(session_id):
                    return self._send(400, {"error": "invalid_session_id"})
                try:
                    limit = int(query.get("limit", ["40"])[0])
                except (TypeError, ValueError):
                    return self._send(400, {"error": "invalid_limit"})
                if not 1 <= limit <= 200:
                    return self._send(400, {"error": "invalid_limit"})
                return self._send(200, {
                    "session_id": session_id,
                    "messages": runtime.store.history(session_id, limit),
                })

            if path == "/v1/agents/due":
                return self._send(200, {"agents": [_safe_agent(agent) for agent in orchestration.due_agents()]})
            agent_match = re.fullmatch(r"/v1/agents/([^/]+)", path)
            if agent_match:
                agent_id = unquote(agent_match.group(1))
                if not _valid_resource_id(agent_id):
                    return self._send(400, {"error": "invalid_agent_id"})
                agent = orchestration.get_agent(agent_id)
                if agent is None:
                    return self._send(404, {"error": "agent_not_found"})
                return self._send(200, {"agent": _safe_agent(agent)})
            if path == "/v1/agents":
                state = query.get("state", [None])[0]
                if state is not None and state not in AGENT_STATES:
                    return self._send(400, {"error": "invalid_agent_state"})
                return self._send(200, {"agents": [_safe_agent(agent) for agent in orchestration.list_agents(state)]})
            if path == "/v1/goals":
                status = query.get("status", [None])[0]
                if status is not None and (not status or len(status) > 40):
                    return self._send(400, {"error": "invalid_goal_status"})
                return self._send(200, {"goals": orchestration.list_goals(status)})
            if path == "/v1/approvals":
                status = query.get("status", ["pending"])[0]
                if status not in APPROVAL_STATES:
                    return self._send(400, {"error": "invalid_approval_status"})
                return self._send(200, {"approvals": orchestration.list_approvals(status)})
            if path == "/v1/budgets":
                return self._send(200, {"budgets": orchestration.budgets()})

            prefix = "/v1/runs/"
            if path.startswith(prefix):
                run_id = unquote(path[len(prefix):])
                if not _valid_resource_id(run_id):
                    return self._send(400, {"error": "invalid_run_id"})
                run = orchestration.get_run(run_id)
                if run is None:
                    return self._send(404, {"error": "run_not_found"})
                return self._send(200, {"run": run})
            return self._send(404, {"error": "not_found"})

        def do_DELETE(self):
            parsed = urlsplit(self.path)
            prefix = "/v1/sessions/"
            if not parsed.path.startswith(prefix):
                return self._send(404, {"error": "not_found"})
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            session_id = parsed.path[len(prefix):]
            if not _valid_session_id(session_id):
                return self._send(400, {"error": "invalid_session_id"})
            if not runtime.store.delete_session(session_id):
                return self._send(404, {"error": "session_not_found"})
            return self._send(200, {"deleted": True, "session_id": session_id})

        def do_PATCH(self):
            if not self._control_authorized():
                return self._send(401, {"error": "control_plane_authentication_required"})
            parts = urlsplit(self.path).path.strip("/").split("/")
            if len(parts) != 3 or parts[:2] != ["v1", "agents"]:
                return self._send(404, {"error": "not_found"})
            agent_id = unquote(parts[2])
            if not _valid_resource_id(agent_id):
                return self._send(400, {"error": "invalid_agent_id"})
            payload = self._read_object()
            if payload is None:
                return
            if (set(payload) != {"state"} or not isinstance(payload.get("state"), str)
                    or payload.get("state") not in AGENT_STATES):
                return self._send(400, {"error": "invalid_agent_state"})
            agent = runtime.tools.orchestration.set_agent_state(agent_id, payload["state"])
            if agent is None:
                return self._send(404, {"error": "agent_not_found"})
            return self._send(200, {"agent": _safe_agent(agent)})

        def do_POST(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            path = urlsplit(self.path).path
            control_route = (
                path.startswith(("/v1/agents", "/v1/goals", "/v1/approvals",
                                 "/v1/budgets", "/v1/runs"))
            )
            if control_route and not self._control_authorized():
                return self._send(401, {"error": "control_plane_authentication_required"})
            orchestration = runtime.tools.orchestration

            if path == "/v1/chat":
                payload = self._read_object()
                if payload is None:
                    return
                session_id = payload.get("session_id")
                if session_id is not None and not _valid_session_id(session_id):
                    return self._send(400, {"error": "invalid_session_id"})
                try:
                    result = runtime.chat(payload.get("message"), session_id)
                except ValueError as exc:
                    return self._send(400, {"error": str(exc)})
                except RuntimeError as exc:
                    return self._send(502, {"error": str(exc)})
                return self._send(200, result)

            if path == "/v1/agents":
                payload = self._read_object()
                if payload is None:
                    return
                name = self._text(payload, "name", 120)
                adapter = self._text(payload, "adapter", 64)
                model = self._text(payload, "model", 200, required=False)
                role_value = self._text(payload, "role", 80, required=False)
                role = role_value or "agent"
                config = payload.get("config", {})
                heartbeat = payload.get("heartbeat_seconds", 0)
                if (name is None or adapter is None or model is None
                        or role_value is None or not isinstance(config, dict)
                        or isinstance(heartbeat, bool) or not isinstance(heartbeat, int)
                        or not 0 <= heartbeat <= 86400):
                    return self._send(400, {"error": "invalid_agent"})
                try:
                    agent = orchestration.register_agent(name, adapter, model or None, role, config, heartbeat)
                except (TypeError, ValueError) as exc:
                    return self._send(400, {"error": str(exc)})
                return self._send(201, {"agent": _safe_agent(agent)})

            agent_heartbeat = re.fullmatch(r"/v1/agents/([^/]+)/heartbeat", path)
            if agent_heartbeat:
                agent_id = unquote(agent_heartbeat.group(1))
                if not _valid_resource_id(agent_id):
                    return self._send(400, {"error": "invalid_agent_id"})
                payload = self._read_object()
                if payload is None:
                    return
                if payload:
                    return self._send(400, {"error": "heartbeat_body_must_be_empty"})
                agent = orchestration.mark_heartbeat(agent_id)
                if agent is None:
                    return self._send(409, {"error": "agent_not_active"})
                return self._send(200, {"agent": _safe_agent(agent)})

            agent_execute = re.fullmatch(r"/v1/agents/([^/]+)/execute", path)
            if agent_execute:
                agent_id = unquote(agent_execute.group(1))
                if not _valid_resource_id(agent_id):
                    return self._send(400, {"error": "invalid_agent_id"})
                payload = self._read_object()
                if payload is None:
                    return
                prompt = self._text(payload, "prompt", 10000)
                if prompt is None or set(payload) != {"prompt"}:
                    return self._send(400, {"error": "invalid_agent_prompt"})
                try:
                    result = json.loads(runtime.tools.execute(
                        "agents.execute", {"agent_id": agent_id, "prompt": prompt}
                    ))
                except (TypeError, ValueError, json.JSONDecodeError):
                    return self._send(502, {"error": "agent_execution_failed"})
                if isinstance(result, dict) and result.get("error"):
                    status = 502 if result.get("type") else 400
                    return self._send(status, result)
                return self._send(200, result)

            if path == "/v1/goals":
                payload = self._read_object()
                if payload is None:
                    return
                title = self._text(payload, "title", 200)
                description = self._text(payload, "description", 2000, required=False)
                parent_id = payload.get("parent_id")
                owner_agent_id = payload.get("owner_agent_id")
                if (title is None or description is None
                        or (parent_id is not None and not _valid_resource_id(parent_id))
                        or (owner_agent_id is not None and not _valid_resource_id(owner_agent_id))):
                    return self._send(400, {"error": "invalid_goal"})
                try:
                    goal = orchestration.create_goal(title, description, parent_id, owner_agent_id)
                except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
                    return self._send(400, {"error": str(exc)})
                return self._send(201, {"goal": goal})

            if path == "/v1/approvals":
                payload = self._read_object()
                if payload is None:
                    return
                action = self._text(payload, "action", 120)
                details = payload.get("details")
                agent_id = payload.get("agent_id")
                if (action is None or not isinstance(details, dict)
                        or (agent_id is not None and not _valid_resource_id(agent_id))):
                    return self._send(400, {"error": "invalid_approval"})
                try:
                    approval = orchestration.request_approval(action, details, agent_id)
                except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
                    return self._send(400, {"error": str(exc)})
                return self._send(201, {"approval": approval})

            decision = re.fullmatch(r"/v1/approvals/([^/]+)/decision", path)
            if decision:
                approval_id = unquote(decision.group(1))
                if not _valid_resource_id(approval_id):
                    return self._send(400, {"error": "invalid_approval_id"})
                payload = self._read_object()
                if payload is None:
                    return
                state = payload.get("decision")
                decided_by = self._text(payload, "decided_by", 120)
                note = self._text(payload, "note", 1000, required=False)
                if not isinstance(state, str) or state not in _DECISIONS or decided_by is None or note is None:
                    return self._send(400, {"error": "invalid_approval_decision"})
                approval = orchestration.decide_approval(approval_id, state, decided_by, note)
                if approval is None:
                    return self._send(409, {"error": "approval_not_pending"})
                return self._send(200, {"approval": approval})

            if path == "/v1/budgets":
                payload = self._read_object()
                if payload is None:
                    return
                amount = payload.get("limit_amount")
                period = self._text(payload, "period", 40)
                agent_id = payload.get("agent_id")
                currency = payload.get("currency", "USD")
                if (not _finite_nonnegative(amount)
                        or period is None
                        or (agent_id is not None and not _valid_resource_id(agent_id))
                        or not isinstance(currency, str) or not re.fullmatch(r"[A-Za-z]{3}", currency)):
                    return self._send(400, {"error": "invalid_budget"})
                try:
                    budget = orchestration.set_budget(amount, period, agent_id, currency)
                except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
                    return self._send(400, {"error": str(exc)})
                return self._send(200, {"budget": budget})

            if path == "/v1/budgets/costs":
                payload = self._read_object()
                if payload is None:
                    return
                amount = payload.get("amount")
                period = self._text(payload, "period", 40)
                agent_id = payload.get("agent_id")
                if (not _finite_nonnegative(amount)
                        or period is None
                        or (agent_id is not None and not _valid_resource_id(agent_id))):
                    return self._send(400, {"error": "invalid_cost"})
                try:
                    budget = orchestration.record_cost(amount, period, agent_id)
                except ValueError as exc:
                    status = 409 if "exceed" in str(exc).lower() else 400
                    return self._send(status, {"error": str(exc)})
                return self._send(200, {"budget": budget})

            if path == "/v1/runs":
                payload = self._read_object()
                if payload is None:
                    return
                agent_id = payload.get("agent_id")
                task_id = payload.get("task_id")
                input_data = payload.get("input_data", {})
                if (not _valid_resource_id(agent_id)
                        or (task_id is not None and not _valid_resource_id(task_id))
                        or not isinstance(input_data, dict)):
                    return self._send(400, {"error": "invalid_run"})
                try:
                    run = orchestration.start_run(agent_id, task_id, input_data)
                except ValueError as exc:
                    return self._send(400, {"error": str(exc)})
                return self._send(201, {"run": run})

            finish = re.fullmatch(r"/v1/runs/([^/]+)/finish", path)
            if finish:
                run_id = unquote(finish.group(1))
                if not _valid_resource_id(run_id):
                    return self._send(400, {"error": "invalid_run_id"})
                payload = self._read_object()
                if payload is None:
                    return
                status = payload.get("status")
                output = payload.get("output", {})
                cost = payload.get("cost_amount", 0)
                if (not isinstance(status, str) or status not in {"succeeded", "failed", "cancelled"}
                        or not isinstance(output, dict)
                        or not _finite_nonnegative(cost)):
                    return self._send(400, {"error": "invalid_run_result"})
                run = orchestration.finish_run(run_id, status, output, cost)
                if run is None:
                    return self._send(409, {"error": "run_not_running"})
                return self._send(200, {"run": run})

            return self._send(404, {"error": "not_found"})

        def log_message(self, fmt, *args):
            return

    return Handler


def serve():
    host = os.getenv("ASTRO_AI_HOST", "127.0.0.1")
    port = int(os.getenv("ASTRO_AI_PORT", "8765"))
    token = os.getenv("ASTRO_AI_API_TOKEN", "")
    if host not in {"127.0.0.1", "::1", "localhost"} and len(token) < 24:
        raise RuntimeError("Non-loopback binding requires ASTRO_AI_API_TOKEN of at least 24 characters")
    runtime = AgentRuntime()
    server = ThreadingHTTPServer((host, port), make_handler(runtime, token))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.close()


if __name__ == "__main__":
    serve()
