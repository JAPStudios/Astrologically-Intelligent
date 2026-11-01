"""Authenticated API integrations for external automation and agent platforms."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class IntegrationError(RuntimeError):
    pass


class JsonApiClient:
    """Small bounded JSON client for explicitly configured trusted service URLs."""

    def __init__(self, base_url: str, token: str, service: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.service = service
        self.timeout = timeout
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{service} base URL must be an absolute HTTP(S) URL")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(f"{service} credentials require HTTPS except for localhost")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                query: dict[str, Any] | None = None) -> Any:
        if not (path.startswith("/api/") or (self.service == "OpenClaw" and path == "/tools/invoke")) or ".." in path.split("/"):
            raise ValueError("Invalid API path")
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise IntegrationError(f"{self.service} response exceeded 2 MB")
                return json.loads(body.decode("utf-8")) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", errors="replace")
            raise IntegrationError(f"{self.service} API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise IntegrationError(f"Could not connect to {self.service}: {exc.reason}") from exc


class N8nClient:
    """Client for the n8n public REST API (X-N8N-API-KEY authentication)."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("n8n base URL must be an absolute HTTP(S) URL")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("n8n API credentials require HTTPS except for localhost")

    @classmethod
    def from_env(cls) -> "N8nClient":
        key = os.getenv("N8N_API_KEY", "").strip()
        if not key:
            raise IntegrationError("N8N_API_KEY is not configured")
        return cls(os.getenv("N8N_BASE_URL", "http://localhost:5678"), key)

    def _request(self, method: str, path: str, query: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/api/v1/") or ".." in path.split("/"):
            raise ValueError("Invalid n8n API path")
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        request = urllib.request.Request(url, headers={"X-N8N-API-KEY": self.api_key, "Accept": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise IntegrationError("n8n response exceeded 2 MB")
                return json.loads(body.decode("utf-8")) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", errors="replace")
            raise IntegrationError(f"n8n API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise IntegrationError(f"Could not connect to n8n: {exc.reason}") from exc

    @staticmethod
    def _workflow_id(workflow_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(workflow_id)):
            raise ValueError("Invalid n8n workflow ID")
        return str(workflow_id)

    def list_workflows(self, limit: int = 100, cursor: str | None = None) -> Any:
        if not 1 <= int(limit) <= 250:
            raise ValueError("limit must be between 1 and 250")
        query: dict[str, Any] = {"limit": int(limit)}
        if cursor:
            query["cursor"] = cursor
        return self._request("GET", "/api/v1/workflows", query)

    def get_workflow(self, workflow_id: str) -> Any:
        return self._request("GET", f"/api/v1/workflows/{self._workflow_id(workflow_id)}")

    def set_workflow_active(self, workflow_id: str, active: bool) -> Any:
        action = "activate" if active else "deactivate"
        return self._request("POST", f"/api/v1/workflows/{self._workflow_id(workflow_id)}/{action}")


class PaperclipClient:
    """Paperclip company-scoped agent, issue, goal, and approval API client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.http = JsonApiClient(base_url, api_key, "Paperclip", timeout)

    @classmethod
    def from_env(cls) -> "PaperclipClient":
        key = os.getenv("PAPERCLIP_API_KEY", "").strip()
        if not key:
            raise IntegrationError("PAPERCLIP_API_KEY is not configured")
        base = os.getenv("PAPERCLIP_BASE_URL", "http://localhost:3100")
        return cls(base, key)

    @staticmethod
    def _id(value: str, label: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(value)):
            raise ValueError(f"Invalid Paperclip {label}")
        return str(value)

    def list_agents(self, company_id: str) -> Any:
        company = self._id(company_id, "company ID")
        return self.http.request("GET", f"/api/companies/{company}/agents")

    def list_issues(self, company_id: str, status: str | None = None,
                    assignee_agent_id: str | None = None, project_id: str | None = None) -> Any:
        company = self._id(company_id, "company ID")
        query: dict[str, Any] = {}
        if status:
            if not re.fullmatch(r"[a-z_,]{1,100}", status):
                raise ValueError("Invalid issue status filter")
            query["status"] = status
        if assignee_agent_id:
            query["assigneeAgentId"] = self._id(assignee_agent_id, "agent ID")
        if project_id:
            query["projectId"] = self._id(project_id, "project ID")
        return self.http.request("GET", f"/api/companies/{company}/issues", query=query)

    def create_issue(self, company_id: str, title: str, description: str = "",
                     status: str = "todo", priority: str = "medium",
                     assignee_agent_id: str | None = None, project_id: str | None = None,
                     goal_id: str | None = None) -> Any:
        company = self._id(company_id, "company ID")
        if not title.strip():
            raise ValueError("Issue title is required")
        if status not in {"backlog", "todo", "in_progress", "blocked", "in_review"}:
            raise ValueError("Invalid Paperclip issue status")
        if priority not in {"critical", "high", "medium", "low"}:
            raise ValueError("Invalid Paperclip issue priority")
        payload: dict[str, Any] = {"title": title.strip(), "description": description,
                                   "status": status, "priority": priority}
        if assignee_agent_id:
            payload["assigneeAgentId"] = self._id(assignee_agent_id, "agent ID")
        if project_id:
            payload["projectId"] = self._id(project_id, "project ID")
        if goal_id:
            payload["goalId"] = self._id(goal_id, "goal ID")
        return self.http.request("POST", f"/api/companies/{company}/issues", payload)

    def list_approvals(self, company_id: str, status: str | None = None) -> Any:
        company = self._id(company_id, "company ID")
        query = {"status": status} if status else None
        return self.http.request("GET", f"/api/companies/{company}/approvals", query=query)

    def create_goal(self, company_id: str, title: str, description: str = "") -> Any:
        company = self._id(company_id, "company ID")
        if not title.strip():
            raise ValueError("Goal title is required")
        return self.http.request("POST", f"/api/companies/{company}/goals",
                                 {"title": title.strip(), "description": description})




class OpenClawClient:
    """Narrow read-only client for OpenClaw Gateway's authenticated HTTP tool API."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        if not token.strip():
            raise IntegrationError("OpenClaw Gateway token is required")
        self.http = JsonApiClient(base_url, token, "OpenClaw", timeout)

    @classmethod
    def from_env(cls) -> "OpenClawClient":
        token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "").strip()
        if not token:
            raise IntegrationError("OPENCLAW_GATEWAY_TOKEN is not configured")
        return cls(os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789"), token)

    def list_sessions(self, session_key: str = "main") -> Any:
        if not re.fullmatch(r"[A-Za-z0-9_:@./-]{1,256}", session_key):
            raise ValueError("Invalid OpenClaw session key")
        # Keep this integration read-only. The Gateway token is an operator credential;
        # no arbitrary tool name or mutating tool arguments are accepted here.
        return self.http.request("POST", "/tools/invoke", {
            "tool": "sessions_list", "args": {}, "sessionKey": session_key,
        })


class PerplexityClient:
    """Perplexity Search API client using the documented /search endpoint."""

    def __init__(self, api_key: str, base_url: str = "https://api.perplexity.ai", timeout: float = 30.0):
        if not api_key.strip():
            raise IntegrationError("Perplexity API key is required")
        self.http = JsonApiClient(base_url, api_key, "Perplexity", timeout)

    @classmethod
    def from_env(cls) -> "PerplexityClient":
        key = os.getenv("PERPLEXITY_API_KEY", "").strip()
        if not key:
            raise IntegrationError("PERPLEXITY_API_KEY is not configured")
        return cls(key, os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai"))

    def search(self, query: str, max_results: int = 5) -> Any:
        if not query.strip():
            raise ValueError("Search query is required")
        if not 1 <= int(max_results) <= 20:
            raise ValueError("max_results must be between 1 and 20")
        return self.http.request("POST", "/search", {"query": query.strip(), "max_results": int(max_results)})


def n8n_client_from_env() -> N8nClient:
    return N8nClient.from_env()


def paperclip_client_from_env() -> PaperclipClient:
    return PaperclipClient.from_env()


def perplexity_client_from_env() -> PerplexityClient:
    return PerplexityClient.from_env()


def openclaw_client_from_env() -> OpenClawClient:
    return OpenClawClient.from_env()
