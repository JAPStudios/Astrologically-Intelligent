import httpx

from src.peanut_browsing import PeanutBrowsingClient
from src.settings import DEFAULT_SETTINGS
from services.search import core, providers


def test_peanut_browsing_sync_client_uses_first_party_index_contract():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, json={
            "status": "ok",
            "totalResults": 2,
            "results": [
                {"title": "Example", "url": "https://example.org/page", "snippet": "Indexed page", "score": 0.9},
                {"title": "Unsafe", "url": "file:///etc/passwd", "snippet": "not a web result"},
            ],
        })

    transport = httpx.MockTransport(handler)
    client = PeanutBrowsingClient(
        base_url="https://peanut.example",
        api_key="test-key",
        sync_client_factory=lambda **kwargs: httpx.Client(transport=transport, **kwargs),
    )
    result = client.search_sync("first party search", limit=7, offset=3)

    assert seen["url"].startswith("https://peanut.example/index/search?")
    assert "q=first+party+search" in seen["url"]
    assert "limit=7" in seen["url"]
    assert "offset=3" in seen["url"]
    assert seen["key"] == "test-key"
    assert result["totalResults"] == 2
    assert [row["url"] for row in result["results"]] == ["https://example.org/page"]
    assert result["results"][0]["engine"] == "Peanut Browsing"


def test_peanut_browsing_is_the_default_search_provider():
    assert DEFAULT_SETTINGS["search_provider"] == "peanut_browsing"
    assert DEFAULT_SETTINGS["search_fallback_chain"] == []


def test_peanut_provider_requires_its_gateway_and_key(monkeypatch):
    monkeypatch.delenv("PEANUT_SEARCH_API_URL", raising=False)
    monkeypatch.delenv("PEANUT_SEARCH_API_KEY", raising=False)
    monkeypatch.setattr(providers, "_get_search_settings", lambda: {
        "search_url": "https://peanut.example",
        "search_api_key": "test-key",
    })
    assert providers.provider_configured("peanut_browsing") is True

    monkeypatch.setattr(providers, "_get_search_settings", lambda: {
        "search_url": "https://peanut.example",
    })
    assert providers.provider_configured("peanut_browsing") is False


def test_peanut_provider_calls_the_first_party_client(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, *, base_url, api_key):
            seen["base_url"] = base_url
            seen["api_key"] = api_key

        def search_sync(self, query, *, limit):
            seen["query"] = query
            seen["limit"] = limit
            return {"results": [{"title": "Example", "url": "https://example.org", "snippet": "indexed"}]}

    monkeypatch.setattr(providers, "_get_search_instance", lambda provider: "https://peanut.example")
    monkeypatch.setattr(providers, "_get_provider_key", lambda provider: "test-key")
    monkeypatch.setattr("src.peanut_browsing.PeanutBrowsingClient", FakeClient)

    results = providers.peanut_browsing_search("JAPStudios", count=12)

    assert seen == {
        "base_url": "https://peanut.example",
        "api_key": "test-key",
        "query": "JAPStudios",
        "limit": 12,
    }
    assert results[0]["title"] == "Example"


def test_peanut_provider_has_no_competing_search_fallback(monkeypatch):
    monkeypatch.setattr(core, "_get_search_settings", lambda: {
        "search_fallback_chain": ["duckduckgo", "brave"],
    })
    monkeypatch.setattr(providers, "provider_configured", lambda _provider: True)

    assert core._build_provider_chain("peanut_browsing") == ["peanut_browsing"]


def test_core_provider_dispatch_uses_peanut_browsing(monkeypatch):
    called = {}
    monkeypatch.setattr(providers, "peanut_browsing_search", lambda query, count, time_filter=None: (
        called.update({"query": query, "count": count, "time_filter": time_filter}) or [{"url": "https://example.org"}]
    ))
    results = core._call_provider("peanut_browsing", "query", 8, "week")
    assert results == [{"url": "https://example.org"}]
    assert called == {"query": "query", "count": 8, "time_filter": "week"}
