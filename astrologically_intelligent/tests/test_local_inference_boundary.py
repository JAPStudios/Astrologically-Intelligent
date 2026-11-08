"""Security boundary tests for local-only Astrologically Intelligent inference."""
import pytest

from src.llm_core import (
    _require_local_inference_endpoint,
    llm_call,
    llm_call_async,
    stream_llm,
)


@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1",
    "https://api.anthropic.com",
    "https://generativelanguage.googleapis.com/v1beta",
    "https://api.x.ai/v1",
    "https://api.deepseek.com/v1",
    "https://api.perplexity.ai",
])
def test_public_model_provider_endpoints_are_rejected(url):
    with pytest.raises(RuntimeError, match="Remote model-provider inference is disabled"):
        _require_local_inference_endpoint(url)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:11434/v1",
    "http://localhost:1234/v1",
    "http://192.168.1.20:8000/v1",
])
def test_local_and_private_model_endpoints_are_allowed(url):
    assert _require_local_inference_endpoint(url) == url


@pytest.mark.parametrize("url", [
    "",
    "not-a-url",
    "file:///tmp/model",
    "https://user:password@localhost/v1",
])
def test_invalid_model_endpoints_are_rejected(url):
    with pytest.raises((ValueError, RuntimeError)):
        _require_local_inference_endpoint(url)


def test_sync_inference_rejects_remote_endpoint_before_network_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network request must not be attempted")

    monkeypatch.setattr("src.llm_core.httpx.post", forbidden)
    with pytest.raises(RuntimeError, match="Remote model-provider inference is disabled"):
        llm_call("https://api.openai.com/v1", "model", [{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_async_inference_rejects_remote_endpoint_before_network_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network request must not be attempted")

    monkeypatch.setattr("src.llm_core.httpx.AsyncClient", forbidden)
    with pytest.raises(RuntimeError, match="Remote model-provider inference is disabled"):
        await llm_call_async(
            "https://api.anthropic.com", "model", [{"role": "user", "content": "test"}]
        )


@pytest.mark.asyncio
async def test_streaming_inference_rejects_remote_endpoint_before_network_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network request must not be attempted")

    monkeypatch.setattr("src.llm_core.httpx.AsyncClient", forbidden)
    stream = stream_llm(
        "https://generativelanguage.googleapis.com/v1beta",
        "model",
        [{"role": "user", "content": "test"}],
    )
    with pytest.raises(RuntimeError, match="Remote model-provider inference is disabled"):
        await anext(stream)
