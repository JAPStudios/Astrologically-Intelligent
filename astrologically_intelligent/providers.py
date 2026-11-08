"""Local-only model transport for Astrologically Intelligent."""
from __future__ import annotations

import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 90.0


def _require_loopback_url(value: str) -> str:
    """Reject remote endpoints so prompts cannot be routed to third-party models."""
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("The local model endpoint must be an HTTP(S) loopback URL")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise RuntimeError("The local model endpoint must not contain credentials, query, or fragment")
    hostname = parsed.hostname.rstrip(".").lower()
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if not is_loopback:
        raise RuntimeError("Remote model endpoints are disabled; configure a model served on loopback")
    return value.rstrip("/")


class ChatCompletionsProvider:
    """OpenAI-compatible protocol adapter restricted to a local inference server.

    The protocol is used only as a wire format. This class cannot connect to
    OpenAI or another remote model provider.
    """

    def __init__(self, config: ProviderConfig):
        object.__setattr__(self, "config", ProviderConfig(
            _require_loopback_url(config.base_url), config.api_key, config.model, config.timeout
        ))

    @classmethod
    def from_env(
        cls,
        *,
        default_base_url: str = "http://127.0.0.1:11434/v1",
        default_model: str = "",
    ) -> "ChatCompletionsProvider":
        base_url = _require_loopback_url(os.getenv("ASTRO_AI_BASE_URL", default_base_url))
        model = os.getenv("ASTRO_AI_MODEL", default_model).strip()
        if not model:
            raise RuntimeError("Set ASTRO_AI_MODEL to the exact installed local model identifier")
        return cls(ProviderConfig(base_url, os.getenv("ASTRO_AI_API_KEY", ""), model))

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        result = _post_json(
            f"{self.config.base_url}/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
            timeout if timeout is not None else self.config.timeout,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Local model response must be a JSON object")
        choices = result.get("choices")
        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(choices[0], dict)
            or not isinstance(choices[0].get("message"), dict)
        ):
            raise RuntimeError("Local model response did not contain choices[0].message")
        return choices[0]["message"]


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST JSON to a validated local endpoint with bounded transient retries."""
    import time

    _require_loopback_url(url.rsplit("/chat/completions", 1)[0])
    request_headers = {"Content-Type": "application/json", **headers}
    body = json.dumps(payload).encode("utf-8")
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504, 507}
    last_error = None

    for attempt in range(4):
        request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise RuntimeError("Local model returned a non-object JSON response")
            return result
        except urllib.error.HTTPError as exc:
            if exc.code not in retryable_statuses or attempt == 3:
                raise RuntimeError(f"Local model returned HTTP {exc.code}") from exc
            last_error = exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 0.25 * (2 ** attempt)
            time.sleep(min(max(delay, 0.0), 2.0))
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Local model connection failed ({type(exc).__name__})") from exc
            last_error = exc
            time.sleep(0.25 * (2 ** attempt))

    raise RuntimeError("Local model request failed after retries") from last_error


def provider_from_env() -> ChatCompletionsProvider:
    """Create the local inference provider; remote provider selections are rejected."""
    name = os.getenv("ASTRO_AI_PROVIDER", "local").strip().lower()
    if name not in {"", "local"}:
        raise RuntimeError(
            "Only the local inference provider is supported; third-party model providers are disabled"
        )
    return ChatCompletionsProvider.from_env()
