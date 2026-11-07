"""Authenticated FastAPI bridge to the persistent agent runtime."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Callable, Any

from fastapi import APIRouter, HTTPException, Request

from src.auth_helpers import effective_user

_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_LOCAL_CLIENTS = {"127.0.0.1", "::1", "testclient"}


def _ensure_repository_import_path() -> None:
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)


class AgentRuntimeRegistry:
    """Keep one isolated runtime database and lock per authenticated owner."""

    def __init__(self, data_dir: str | os.PathLike[str], runtime_factory: Callable[[Any], Any] | None = None):
        self._root = Path(data_dir) / "agent_runtime"
        self._runtime_factory = runtime_factory
        self._entries: dict[str, dict[str, Any]] = {}
        self._guard = threading.RLock()

    def _entry(self, owner: str) -> dict[str, Any]:
        if not isinstance(owner, str) or not owner:
            raise ValueError("An authenticated owner is required.")
        with self._guard:
            entry = self._entries.get(owner)
            if entry is None:
                _ensure_repository_import_path()
                from astrologically_intelligent.storage import Store

                self._root.mkdir(parents=True, exist_ok=True)
                filename = hashlib.sha256(owner.encode("utf-8")).hexdigest() + ".sqlite3"
                store = Store(str(self._root / filename))
                entry = {"store": store, "runtime": None, "lock": threading.RLock()}
                self._entries[owner] = entry
            return entry

    def runtime(self, owner: str):
        entry = self._entry(owner)
        with entry["lock"]:
            if entry["runtime"] is None:
                if self._runtime_factory is not None:
                    runtime = self._runtime_factory(entry["store"])
                else:
                    _ensure_repository_import_path()
                    from astrologically_intelligent.providers import provider_from_env
                    from astrologically_intelligent.runtime import AgentRuntime

                    runtime = AgentRuntime(provider=provider_from_env(), store=entry["store"])
                entry["runtime"] = runtime
            return entry["runtime"], entry["lock"]

    def history(self, owner: str, session_id: str) -> list[dict[str, str]]:
        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
            raise ValueError("session_id must contain 1-128 letters, numbers, hyphens, or underscores")
        entry = self._entry(owner)
        with entry["lock"]:
            rows = entry["store"].history(session_id, 40)
            return [
                {"role": row["role"], "content": row["content"]}
                for row in rows
                if row.get("role") in {"user", "assistant"}
                and isinstance(row.get("content"), str)
                and row["content"].strip()
            ]

    def close(self) -> None:
        with self._guard:
            entries = list(self._entries.values())
            self._entries.clear()
        for entry in entries:
            runtime = entry["runtime"]
            close = getattr(runtime, "close", None) if runtime is not None else None
            if callable(close):
                close()
            else:
                entry["store"].close()


def create_agent_api_router(
    registry: AgentRuntimeRegistry,
    *,
    auth_enabled: bool = True,
) -> APIRouter:
    router = APIRouter(tags=["agent_runtime"])

    def _owner(request: Request) -> str:
        is_api_token = bool(getattr(request.state, "api_token", False))
        if is_api_token:
            scopes = set(getattr(request.state, "api_token_scopes", []) or [])
            if "chat" not in scopes:
                raise HTTPException(status_code=403, detail="This API token does not have the chat scope.")

        owner = effective_user(request)
        if auth_enabled:
            if not owner or owner == "api":
                raise HTTPException(status_code=401, detail="Authentication is required.")
            auth_manager = getattr(request.app.state, "auth_manager", None)
            if auth_manager is None or not auth_manager.is_admin(owner):
                raise HTTPException(status_code=403, detail="The agent runtime API is restricted to administrator accounts.")
            return owner

        host = request.client.host if request.client else None
        if host not in _LOCAL_CLIENTS:
            expected = os.getenv("ASTRO_AI_API_TOKEN", "").strip()
            supplied = request.headers.get("Authorization", "")
            if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
                raise HTTPException(status_code=401, detail="A configured bearer token is required for remote access.")
        return owner or "local"

    @router.post("/v1/chat")
    async def chat(request: Request):
        owner = _owner(request)
        raw = await request.body()
        if len(raw) > 1_000_000:
            raise HTTPException(status_code=413, detail="Request body exceeds the 1 MB limit.")
        try:
            payload = json.loads(raw or b"{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="Request body must be valid JSON.")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")
        message = payload.get("message")
        session_id = payload.get("session_id")
        if not isinstance(message, str) or not message.strip():
            raise HTTPException(status_code=400, detail="message must be a non-empty string.")
        if session_id is not None and not isinstance(session_id, str):
            raise HTTPException(status_code=400, detail="session_id must be a string.")
        try:
            runtime, lock = registry.runtime(owner)
            with lock:
                return runtime.chat(message, session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=503, detail="The agent runtime is unavailable or not configured.")

    @router.get("/v1/sessions/{session_id}")
    def history(request: Request, session_id: str):
        owner = _owner(request)
        try:
            return {"session_id": session_id, "messages": registry.history(owner, session_id)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=503, detail="Conversation history is unavailable.")

    return router
