"""Model-provider transports for OpenAI-compatible APIs and Anthropic Messages."""
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
    """Chat Completions transport for OpenAI, xAI, local servers, and compatible gateways."""

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
        result = _post_json(
            f"{self.config.base_url}/chat/completions", payload,
            {"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
            self.config.timeout,
        )
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0].get("message"), dict):
            raise RuntimeError("Provider response did not contain choices[0].message")
        return choices[0]["message"]


class AnthropicMessagesProvider:
    """Anthropic Messages API adapter that preserves the runtime's function-tool contract."""

    def __init__(self, config: ProviderConfig, api_version: str = "2023-06-01"):
        self.config = config
        self.api_version = api_version

    @classmethod
    def from_env(cls) -> "AnthropicMessagesProvider":
        key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ASTRO_AI_API_KEY", "")
        model = os.getenv("ASTRO_AI_MODEL", "claude-sonnet-4-5")
        if not key:
            raise RuntimeError("Set ANTHROPIC_API_KEY or ASTRO_AI_API_KEY for the Anthropic provider")
        return cls(ProviderConfig(os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/"), key, model))

    @staticmethod
    def _messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []
        pending_results: list[dict[str, Any]] = []

        def flush_results():
            if pending_results:
                converted.append({"role": "user", "content": list(pending_results)})
                pending_results.clear()

        for message in messages:
            role = message.get("role")
            if role == "system":
                if message.get("content"):
                    system_parts.append(str(message["content"]))
                continue
            if role == "tool":
                pending_results.append({
                    "type": "tool_result",
                    "tool_use_id": message.get("tool_call_id", ""),
                    "content": str(message.get("content", "")),
                })
                continue
            flush_results()
            if role == "assistant" and message.get("tool_calls"):
                blocks = []
                if message.get("content"):
                    blocks.append({"type": "text", "text": str(message["content"])})
                for call in message["tool_calls"]:
                    fn = call.get("function", {})
                    try:
                        arguments = json.loads(fn.get("arguments") or "{}")
                    except (TypeError, json.JSONDecodeError):
                        arguments = {}
                    blocks.append({
                        "type": "tool_use", "id": call.get("id", ""),
                        "name": fn.get("name", ""), "input": arguments,
                    })
                converted.append({"role": "assistant", "content": blocks})
            elif role in {"user", "assistant"}:
                converted.append({"role": role, "content": str(message.get("content") or "")})
        flush_results()
        # The Messages API requires alternating roles. Merge adjacent same-role
        # entries, which can occur when multiple tool results follow one assistant turn.
        normalized: list[dict[str, Any]] = []
        for item in converted:
            if normalized and normalized[-1]["role"] == item["role"]:
                previous = normalized[-1]["content"]
                current = item["content"]
                normalized[-1]["content"] = (previous if isinstance(previous, list) else [{"type":"text","text":previous}]) + (current if isinstance(current, list) else [{"type":"text","text":current}])
            else:
                normalized.append(item)
        return "\n\n".join(system_parts), normalized

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        system, converted = self._messages(messages)
        payload: dict[str, Any] = {
            "model": self.config.model, "max_tokens": 4096, "messages": converted,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": item["function"]["name"],
                 "description": item["function"].get("description", ""),
                 "input_schema": item["function"].get("parameters", {"type":"object","properties":{}})}
                for item in tools if item.get("type") == "function" and item.get("function")
            ]
        result = _post_json(
            f"{self.config.base_url}/v1/messages", payload,
            {"x-api-key": self.config.api_key, "anthropic-version": self.api_version},
            self.config.timeout,
        )
        content = result.get("content")
        if not isinstance(content, list):
            raise RuntimeError("Anthropic response did not contain a content array")
        text_parts, tool_calls = [], []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""), "type": "function",
                    "function": {"name": block.get("name", ""),
                                 "arguments": json.dumps(block.get("input", {}), ensure_ascii=False)},
                })
        response: dict[str, Any] = {"role": "assistant", "content": "\n".join(text_parts) or None}
        if tool_calls:
            response["tool_calls"] = tool_calls
        return response


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request_headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Provider connection failed: {exc}") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Provider returned a non-object JSON response")
    return result


def provider_from_env():
    """Select a provider using ASTRO_AI_PROVIDER; xAI uses the compatible transport."""
    name = os.getenv("ASTRO_AI_PROVIDER", "openai-compatible").strip().lower()
    if name in {"anthropic", "claude"}:
        return AnthropicMessagesProvider.from_env()
    if name in {"openai", "openai-compatible", "xai", "grok", "perplexity", "local"}:
        return OpenAICompatibleProvider.from_env()
    raise RuntimeError(f"Unsupported ASTRO_AI_PROVIDER: {name}")
