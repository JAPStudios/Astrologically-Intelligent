import json
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import quote
from http.server import ThreadingHTTPServer

from astrologically_intelligent.runtime import AgentRuntime
from astrologically_intelligent.storage import Store
from astrologically_intelligent.server import make_handler


class StubProvider:
    def chat(self, messages, tools):
        return {"content": "agent execution complete", "tool_calls": []}


class HistoryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.runtime = AgentRuntime(provider=object(), store=self.store)
        self.store.add_message("session-1", "user", "First message")
        self.store.add_message("session-1", "assistant", "First reply")
        self.store.add_message("session-2", "user", "Another conversation")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.runtime, "test-token"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.runtime.close()

    def request(self, path, token="test-token", method="GET"):
        request = urllib.request.Request(self.url + path, method=method)
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        return urllib.request.urlopen(request, timeout=3)

    def json_request(self, path, payload=None, token="test-token", method="GET"):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        return urllib.request.urlopen(request, timeout=5)

    def test_history_returns_session_messages_in_chronological_order(self):
        with self.request("/v1/history?session_id=session-1") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["messages"], [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First reply"},
        ])

    def test_sessions_returns_recent_conversation_previews(self):
        with self.request("/v1/sessions") as response:
            payload = json.loads(response.read())
        self.assertEqual([item["session_id"] for item in payload["sessions"]],
                         ["session-2", "session-1"])
        self.assertEqual(payload["sessions"][0]["preview"], "Another conversation")
        self.assertEqual(payload["sessions"][1]["message_count"], 2)

    def test_sessions_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions", token="")
        self.assertEqual(raised.exception.code, 401)

    def test_sessions_rejects_invalid_limits(self):
        for path in ("/v1/sessions?limit=0", "/v1/sessions?limit=101",
                     "/v1/sessions?limit=invalid"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request(path)
            self.assertEqual(raised.exception.code, 400)

    def test_delete_removes_only_the_selected_conversation(self):
        with self.request("/v1/sessions/session-1", method="DELETE") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload, {"deleted": True, "session_id": "session-1"})
        with self.request("/v1/history?session_id=session-1") as response:
            self.assertEqual(json.loads(response.read())["messages"], [])
        with self.request("/v1/history?session_id=session-2") as response:
            self.assertEqual(len(json.loads(response.read())["messages"]), 1)

    def test_delete_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions/session-1", token="", method="DELETE")
        self.assertEqual(raised.exception.code, 401)

    def test_delete_reports_unknown_conversation(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions/missing", method="DELETE")
        self.assertEqual(raised.exception.code, 404)

    def test_health_remains_public(self):
        with urllib.request.urlopen(self.url + "/health", timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["status"], "ok")

    def test_chat_rejects_invalid_session_identifiers_before_runtime(self):
        invalid_ids = (42, {}, "", "session/1", "session-é", "x" * 129)
        for session_id in invalid_ids:
            body = json.dumps({"message": "hello", "session_id": session_id}).encode("utf-8")
            request = urllib.request.Request(
                self.url + "/v1/chat",
                data=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with self.subTest(session_id=repr(session_id)):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(raised.exception.code, 400)
                self.assertEqual(
                    json.loads(raised.exception.read()),
                    {"error": "invalid_session_id"},
                )

    def test_history_rejects_invalid_session_identifiers(self):
        invalid_ids = ("", "session/1", "session-é", "session with spaces", "x" * 129)
        for session_id in invalid_ids:
            path = "/v1/history?session_id=" + quote(session_id, safe="")
            with self.subTest(session_id=repr(session_id)):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    self.request(path)
                self.assertEqual(raised.exception.code, 400)
                self.assertEqual(
                    json.loads(raised.exception.read()),
                    {"error": "invalid_session_id"},
                )

    def test_history_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/history?session_id=session-1", token="")
        self.assertEqual(raised.exception.code, 401)

    def test_history_rejects_missing_session_and_invalid_limits(self):
        for path in ("/v1/history", "/v1/history?session_id=session-1&limit=0",
                     "/v1/history?session_id=session-1&limit=201",
                     "/v1/history?session_id=session-1&limit=invalid"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request(path)
            self.assertEqual(raised.exception.code, 400)

    def test_panmedia_agent_management_api_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/agents", token="")
        self.assertEqual(raised.exception.code, 401)

        # The local chat API may remain token-optional, but control-plane
        # routes must never become unauthenticated when no token is configured.
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.runtime, "")
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            for path, method, body in (
                ("/v1/agents", "GET", None),
                ("/v1/agents", "POST", {"name": "No auth", "adapter": "llm"}),
                ("/v1/goals", "POST", {"title": "No auth"}),
                ("/v1/runs", "POST", {"agent_id": "missing", "input_data": {}}),
            ):
                data = None if body is None else json.dumps(body).encode("utf-8")
                request = urllib.request.Request(
                    url + path, data=data, method=method,
                    headers={"Content-Type": "application/json"} if data is not None else {},
                )
                with self.subTest(path=path, method=method):
                    with self.assertRaises(urllib.error.HTTPError) as denied:
                        urllib.request.urlopen(request, timeout=3)
                    self.assertEqual(denied.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_panmedia_can_register_list_pause_and_execute_agents(self):
        provider = StubProvider()
        self.runtime.provider = provider
        self.runtime.tools.provider = provider
        with self.json_request("/v1/agents", {
            "name": "Research assistant",
            "adapter": "llm",
            "role": "research",
            "config": {"allowed_tools": [], "api_key": "do-not-return", "nested": {"refresh_token": "do-not-return-either"}, "system_prompt": "safe instructions"},
            "heartbeat_seconds": 60,
        }, method="POST") as response:
            self.assertEqual(response.status, 201)
            agent = json.loads(response.read())["agent"]
        self.assertEqual(agent["name"], "Research assistant")
        self.assertEqual(agent["config"]["api_key"], "[REDACTED]")
        self.assertEqual(agent["config"]["nested"]["refresh_token"], "[REDACTED]")
        self.assertEqual(agent["config"]["system_prompt"], "safe instructions")
        with self.json_request("/v1/agents/" + agent["id"] + "/heartbeat", {}, method="POST") as response:
            heartbeat_agent = json.loads(response.read())["agent"]
        self.assertIsNotNone(heartbeat_agent["last_heartbeat"])
        self.assertEqual(heartbeat_agent["config"]["api_key"], "[REDACTED]")
        with self.request("/v1/agents") as response:
            agents = json.loads(response.read())["agents"]
        self.assertEqual([item["id"] for item in agents], [agent["id"]])
        with self.request("/v1/agents/" + agent["id"]) as response:
            lookup = json.loads(response.read())["agent"]
        self.assertEqual(lookup["name"], "Research assistant")
        self.assertEqual(lookup["config"]["nested"]["refresh_token"], "[REDACTED]")
        with self.json_request("/v1/agents/" + agent["id"], {"state": "paused"}, method="PATCH") as response:
            paused_agent = json.loads(response.read())["agent"]
        self.assertEqual(paused_agent["state"], "paused")
        self.assertEqual(paused_agent["config"]["api_key"], "[REDACTED]")
        with self.json_request("/v1/agents/" + agent["id"], {"state": "active"}, method="PATCH") as response:
            self.assertEqual(json.loads(response.read())["agent"]["state"], "active")
        with self.json_request("/v1/agents/" + agent["id"] + "/execute", {"prompt": "Complete this task."}, method="POST") as response:
            result = json.loads(response.read())
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["output"], "agent execution complete")
        with self.request("/v1/runs/" + result["run_id"]) as response:
            run = json.loads(response.read())["run"]
        self.assertEqual(run["status"], "succeeded")
        self.assertEqual(run["agent_id"], agent["id"])

    def test_panmedia_can_manage_goals_approvals_and_budgets(self):
        with self.json_request("/v1/agents", {
            "name": "Operations agent", "adapter": "llm", "config": {},
        }, method="POST") as response:
            agent = json.loads(response.read())["agent"]
        with self.json_request("/v1/goals", {
            "title": "Complete research", "description": "Verify sources.",
            "owner_agent_id": agent["id"],
        }, method="POST") as response:
            goal = json.loads(response.read())["goal"]
        self.assertEqual(goal["owner_agent_id"], agent["id"])
        with self.json_request("/v1/approvals", {
            "action": "publish report", "details": {"report_id": "report-1"},
            "agent_id": agent["id"],
        }, method="POST") as response:
            approval = json.loads(response.read())["approval"]
        with self.request("/v1/approvals?status=pending") as response:
            self.assertEqual(json.loads(response.read())["approvals"][0]["id"], approval["id"])
        with self.json_request("/v1/approvals/" + approval["id"] + "/decision", {
            "decision": "approved", "decided_by": "owner",
        }, method="POST") as response:
            self.assertEqual(json.loads(response.read())["approval"]["status"], "approved")
        with self.json_request("/v1/budgets", {
            "limit_amount": 25, "period": "2026-11", "agent_id": agent["id"],
        }, method="POST") as response:
            budget = json.loads(response.read())["budget"]
        self.assertEqual(budget["limit_amount"], 25)
        with self.json_request("/v1/budgets/costs", {
            "amount": 5, "period": "2026-11", "agent_id": agent["id"],
        }, method="POST") as response:
            self.assertEqual(json.loads(response.read())["budget"]["spent_amount"], 5)

    def test_panmedia_can_retrieve_an_agent_by_id(self):
        with self.json_request("/v1/agents", {
            "name": "Research assistant", "adapter": "llm", "config": {},
        }, method="POST") as response:
            agent = json.loads(response.read())["agent"]
        with self.request("/v1/agents/" + agent["id"]) as response:
            self.assertEqual(json.loads(response.read())["agent"]["id"], agent["id"])
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/agents/" + "f" * 32)
        self.assertEqual(raised.exception.code, 404)

    def test_panmedia_rejects_missing_foreign_key_references_as_client_errors(self):
        cases = [
            ("/v1/goals", {
                "title": "Invalid owner", "owner_agent_id": "missing-agent",
            }),
            ("/v1/goals", {
                "title": "Invalid parent", "parent_id": "missing-goal",
            }),
            ("/v1/approvals", {
                "action": "publish", "details": {}, "agent_id": "missing-agent",
            }),
            ("/v1/budgets", {
                "limit_amount": 10, "period": "2026-11", "agent_id": "missing-agent",
            }),
        ]
        for path, payload in cases:
            with self.subTest(path=path, payload=payload):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    self.json_request(path, payload, method="POST")
                self.assertEqual(raised.exception.code, 400)
                self.assertIn("error", json.loads(raised.exception.read()))

    def test_panmedia_budget_limit_is_enforced(self):
        with self.json_request("/v1/budgets", {
            "limit_amount": 1, "period": "2026-11",
        }, method="POST"):
            pass
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.json_request("/v1/budgets/costs", {
                "amount": 2, "period": "2026-11",
            }, method="POST")
        self.assertEqual(raised.exception.code, 409)


if __name__ == "__main__":
    unittest.main()
