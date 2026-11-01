"""Conversation loop with tool calling, persistent sessions, and bounded execution."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from .providers import OpenAICompatibleProvider
from .storage import Store
from .tools import ToolRegistry

SYSTEM_PROMPT = """You are Astrologically Intelligent, an AI assistant with an astrology-focused product context.
Be explicit about uncertainty. Never invent astronomical positions, birth-chart calculations, transits, or personal data.
Use available tools only for their documented purpose. Ask for missing birth details before offering a personalized interpretation.
Treat astrology as an interpretive framework, not scientifically established prediction.
Keep user data private; do not claim to access accounts or services unless a configured integration actually does so."""


@dataclass
class RuntimeConfig:
    max_tool_rounds: int = 6
    history_limit: int = 40
    system_prompt: str = SYSTEM_PROMPT


class AgentRuntime:
    def __init__(self, provider=None, store: Store | None = None, config: RuntimeConfig | None = None):
        self.provider = provider or OpenAICompatibleProvider.from_env()
        self.store = store or Store(os.getenv("ASTRO_AI_DB", "astrologically_intelligent.sqlite3"))
        self.config = config or RuntimeConfig()
        self.tools = ToolRegistry(self.store)

    def chat(self, message: str, session_id: str | None = None) -> dict[str, str]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        session_id = session_id or uuid.uuid4().hex
        history = self.store.history(session_id, self.config.history_limit)
        self.store.add_message(session_id, "user", message.strip())
        messages = [{"role": "system", "content": self.config.system_prompt}, *history,
                    {"role": "user", "content": message.strip()}]
        for _ in range(self.config.max_tool_rounds + 1):
            response = self.provider.chat(messages, self.tools.definitions())
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                content = response.get("content")
                if not isinstance(content, str):
                    raise RuntimeError("Model returned no text response")
                self.store.add_message(session_id, "assistant", content)
                return {"session_id": session_id, "response": content}
            messages.append(response)
            for call in tool_calls:
                function = call.get("function") or {}
                result = self.tools.execute(function.get("name", ""), function.get("arguments", "{}"))
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""),
                                 "name": function.get("name", ""), "content": result})
        raise RuntimeError("Tool-call limit reached; no final assistant response was produced")
