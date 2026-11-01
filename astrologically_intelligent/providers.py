"""Provider-agnostic chat-completions transport (OpenAI-compatible APIs)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 90.0


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider":
        base_url = os.getenv("ASTRO_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        api_key = os.getenv("ASTRO_AI_API_KEY", "")
        model = os.getenv("ASTRO_AI_MODEL", "gpt-4.1-mini")
        if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
            raise RuntimeError("Set ASTRO_AI_API_KEY (or configure a local provider endpoint)")
        return cls(ProviderConfig(base_url, api_key, model))

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"Provider returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Provider connection failed: {exc}") from exc
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0].get("message"), dict):
            raise RuntimeError("Provider response did not contain choices[0].message")
        return choices[0]["message"]
