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


class N8nClient:
    """Client for the n8n public REST API (API-key authentication)."""

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
        request = urllib.request.Request(
            url, headers={"X-N8N-API-KEY": self.api_key, "Accept": "application/json"},
            method=method,
        )
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


def n8n_client_from_env() -> N8nClient:
    return N8nClient.from_env()
