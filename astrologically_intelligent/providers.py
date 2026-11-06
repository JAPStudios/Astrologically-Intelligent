"""Model-provider transports for OpenAI-compatible APIs and Anthropic Messages."""
from __future__ import annotations

import json
import hashlib
from urllib.parse import quote
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

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, *, temperature: float | None = None, max_tokens: int | None = None, timeout: float | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        result = _post_json(
            f"{self.config.base_url}/chat/completions", payload,
            {"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
            timeout if timeout is not None else self.config.timeout,
        )
        choices = result.get("choices")
        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(choices[0], dict)
            or not isinstance(choices[0].get("message"), dict)
        ):
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
                    if not isinstance(call, dict):
                        raise RuntimeError("Anthropic request contains an invalid tool call")
                    fn = call.get("function")
                    if not isinstance(fn, dict):
                        raise RuntimeError("Anthropic request contains a tool call without a function")
                    raw_arguments = fn.get("arguments", "{}")
                    try:
                        arguments = json.loads(raw_arguments or "{}")
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise RuntimeError("Anthropic request contains malformed tool arguments") from exc
                    if not isinstance(arguments, dict):
                        raise RuntimeError("Anthropic tool arguments must be a JSON object")
                    name = fn.get("name")
                    call_id = call.get("id")
                    if not isinstance(name, str) or not name:
                        raise RuntimeError("Anthropic request contains a tool call without a name")
                    if not isinstance(call_id, str) or not call_id:
                        raise RuntimeError("Anthropic request contains a tool call without an ID")
                    blocks.append({
                        "type": "tool_use", "id": call_id,
                        "name": name, "input": arguments,
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

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, *, temperature: float | None = None, max_tokens: int | None = None, timeout: float | None = None) -> dict[str, Any]:
        system, converted = self._messages(messages)
        payload: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens if max_tokens is not None else 4096,
            "messages": converted,
        }
        if temperature is not None:
            payload["temperature"] = temperature
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
            timeout if timeout is not None else self.config.timeout,
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




def _gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert the runtime's JSON Schema subset to Gemini's Schema shape."""
    if not isinstance(schema, dict):
        return {"type": "STRING"}
    result: dict[str, Any] = {}
    schema_type = schema.get("type")
    nullable = False
    if isinstance(schema_type, list):
        nullable = "null" in schema_type
        schema_type = next((item for item in schema_type if item != "null"), "string")
    if schema_type:
        result["type"] = str(schema_type).upper()
    if nullable or schema.get("nullable") is True:
        result["nullable"] = True
    for key in ("description", "format", "enum", "required", "minimum", "maximum",
                "minItems", "maxItems", "minLength", "maxLength"):
        if key in schema:
            result[key] = schema[key]
    if isinstance(schema.get("properties"), dict):
        result["properties"] = {
            name: _gemini_schema(value) for name, value in schema["properties"].items()
        }
    if isinstance(schema.get("items"), dict):
        result["items"] = _gemini_schema(schema["items"])
    return result


class GeminiGenerateContentProvider:
    """Native Gemini generateContent transport with function calling and signature preservation."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "GeminiGenerateContentProvider":
        key = os.getenv("GEMINI_API_KEY") or os.getenv("ASTRO_AI_API_KEY", "")
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY or ASTRO_AI_API_KEY for the Gemini provider")
        base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        model = os.getenv("ASTRO_AI_MODEL", "gemini-3.8-flash")
        return cls(ProviderConfig(base, key, model))

    @staticmethod
    def _tool_alias(name: str) -> str:
        # Gemini function names are kept portable; runtime tool names may contain dots.
        return "ai_" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def _contents(cls, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        pending_results: list[dict[str, Any]] = []

        def flush_results() -> None:
            if pending_results:
                contents.append({"role": "user", "parts": list(pending_results)})
                pending_results.clear()

        for message in messages:
            role = message.get("role")
            if role == "system":
                if message.get("content"):
                    system_parts.append(str(message["content"]))
                continue
            if role == "tool":
                original_name = str(message.get("name", ""))
                alias = cls._tool_alias(original_name)
                raw = message.get("content", "")
                try:
                    response = json.loads(raw) if isinstance(raw, str) else raw
                except (TypeError, json.JSONDecodeError):
                    response = {"result": str(raw)}
                if not isinstance(response, dict):
                    response = {"result": response}
                function_response: dict[str, Any] = {"name": alias, "response": response}
                call_id = message.get("tool_call_id")
                if call_id:
                    function_response["id"] = call_id
                pending_results.append({"functionResponse": function_response})
                continue
            flush_results()
            if role == "assistant" and isinstance(message.get("_gemini_content"), dict):
                contents.append(message["_gemini_content"])
            elif role in {"user", "assistant"}:
                text = str(message.get("content") or "")
                if text:
                    contents.append({
                        "role": "model" if role == "assistant" else "user",
                        "parts": [{"text": text}],
                    })
        flush_results()
        return "\n\n".join(system_parts), contents

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, *, temperature: float | None = None, max_tokens: int | None = None, timeout: float | None = None) -> dict[str, Any]:
        system, contents = self._contents(messages)
        payload: dict[str, Any] = {"contents": contents}
        generation_config = {}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        aliases: dict[str, str] = {}
        if tools:
            declarations = []
            for item in tools:
                if item.get("type") != "function" or not isinstance(item.get("function"), dict):
                    continue
                fn = item["function"]
                original_name = str(fn.get("name", ""))
                alias = self._tool_alias(original_name)
                if alias in aliases and aliases[alias] != original_name:
                    raise RuntimeError("Gemini tool-name alias collision")
                aliases[alias] = original_name
                declaration: dict[str, Any] = {
                    "name": alias,
                    "description": str(fn.get("description", "")),
                }
                parameters = fn.get("parameters")
                if isinstance(parameters, dict):
                    declaration["parameters"] = _gemini_schema(parameters)
                declarations.append(declaration)
            if declarations:
                payload["tools"] = [{"functionDeclarations": declarations}]
        model = self.config.model.removeprefix("models/")
        if not model or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in model):
            raise ValueError("Invalid Gemini model name")
        result = _post_json(
            f"{self.config.base_url}/models/{quote(model, safe='._-')}:generateContent",
            payload, {"x-goog-api-key": self.config.api_key},
            timeout if timeout is not None else self.config.timeout,
        )
        candidates = result.get("candidates")
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
            raise RuntimeError("Gemini response did not contain candidates[0]")
        candidate = candidates[0]
        content = candidate.get("content")
        if not isinstance(content, dict) or not isinstance(content.get("parts"), list):
            raise RuntimeError("Gemini response did not contain candidate content parts")
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        response_aliases: dict[str, str] = {}
        for part in content["parts"]:
            if not isinstance(part, dict):
                continue
            if isinstance(part.get("text"), str) and not part.get("thought"):
                text_parts.append(part["text"])
            function_call = part.get("functionCall")
            if isinstance(function_call, dict):
                alias = str(function_call.get("name", ""))
                original_name = aliases.get(alias)
                if not original_name:
                    raise RuntimeError("Gemini requested an undeclared function")
                response_aliases[original_name] = alias
                call_id = str(function_call.get("id") or "")
                arguments = function_call.get("args")
                if not isinstance(arguments, dict):
                    arguments = {}
                tool_calls.append({
                    "id": call_id, "type": "function",
                    "function": {
                        "name": original_name,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    },
                })
        response: dict[str, Any] = {"role": "assistant", "content": "\n".join(text_parts) or None}
        if tool_calls:
            # Preserve full model content, including Gemini 3 thought signatures.
            response["tool_calls"] = tool_calls
            response["_gemini_content"] = content
        elif not text_parts:
            reason = candidate.get("finishReason", "unknown")
            raise RuntimeError(f"Gemini returned no text or function call (finishReason={reason})")
        return response


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    """POST JSON with bounded retries for transient provider failures.

    Only availability failures are retried. Authentication, validation and other
    permanent 4xx responses fail immediately. Request bodies remain identical
    across attempts so tool calls and generation settings are not mutated.
    """
    import time

    request_headers = {"Content-Type": "application/json", **headers}
    body = json.dumps(payload).encode("utf-8")
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504, 507, 529}
    max_attempts = 4
    last_error = None

    for attempt in range(max_attempts):
        request = urllib.request.Request(
            url, data=body, headers=request_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise RuntimeError("Provider returned a non-object JSON response")
            return result
        except urllib.error.HTTPError as exc:
            # Provider response bodies are untrusted and may echo submitted data.
            # Keep diagnostics useful without forwarding arbitrary body content.
            if exc.code not in retryable_statuses or attempt == max_attempts - 1:
                raise RuntimeError(f"Provider returned HTTP {exc.code}") from exc
            last_error = exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 0.25 * (2 ** attempt)
            time.sleep(min(max(delay, 0.0), 8.0))
        except (urllib.error.URLError, TimeoutError) as exc:
            # URL errors can include configured endpoints or other sensitive details.
            if attempt == max_attempts - 1:
                raise RuntimeError(
                    f"Provider connection failed ({type(exc).__name__})"
                ) from exc
            last_error = exc
            time.sleep(0.25 * (2 ** attempt))

    raise RuntimeError("Provider request failed after retries") from last_error


def provider_from_env():
    """Select a provider using ASTRO_AI_PROVIDER; xAI uses the compatible transport."""
    name = os.getenv("ASTRO_AI_PROVIDER", "openai-compatible").strip().lower()
    if name in {"anthropic", "claude"}:
        return AnthropicMessagesProvider.from_env()
    if name in {"gemini", "google", "google-gemini"}:
        return GeminiGenerateContentProvider.from_env()
    if name in {"openai", "openai-compatible", "local"}:
        return OpenAICompatibleProvider.from_env()
    if name in {"xai", "grok"}:
        key = os.getenv("XAI_API_KEY") or os.getenv("ASTRO_AI_API_KEY", "")
        base = os.getenv("ASTRO_AI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        model = os.getenv("ASTRO_AI_MODEL", "grok-4.20-non-reasoning")
        if not key:
            raise RuntimeError("Set XAI_API_KEY or ASTRO_AI_API_KEY for xAI")
        return OpenAICompatibleProvider(ProviderConfig(base, key, model))
    if name == "perplexity":
        key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("ASTRO_AI_API_KEY", "")
        base = os.getenv("ASTRO_AI_BASE_URL", os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")).rstrip("/")
        model = os.getenv("ASTRO_AI_MODEL", "sonar")
        if not key:
            raise RuntimeError("Set PERPLEXITY_API_KEY or ASTRO_AI_API_KEY for Perplexity")
        return OpenAICompatibleProvider(ProviderConfig(base, key, model))
    raise RuntimeError(f"Unsupported ASTRO_AI_PROVIDER: {name}")
