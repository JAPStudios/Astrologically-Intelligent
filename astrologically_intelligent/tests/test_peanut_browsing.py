import json
import pytest
import httpx

from src.peanut_browsing import PeanutBrowsingClient, PeanutBrowsingError
from src.tool_security import NON_ADMIN_BLOCKED_TOOLS


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return PeanutBrowsingClient(
        base_url="https://peanut.example",
        api_key="test-key",
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )


@pytest.mark.asyncio
async def test_search_uses_peanut_index_contract_and_returns_sources():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["query"] = request.url.params.get("q")
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, json={
            "status": "ok",
            "totalResults": 1,
            "results": [{
                "title": "Indexed page",
                "url": "https://example.org/page",
                "snippet": "A first-party indexed result.",
                "score": 0.75,
            }],
        })

    result = await make_client(handler).search("first party", limit=7, offset=3)

    assert seen == {
        "path": "/index/search",
        "query": "first party",
        "key": "test-key",
    }
    assert result["totalResults"] == 1
    assert result["results"][0]["engine"] == "Peanut Browsing"
    assert result["results"][0]["url"] == "https://example.org/page"


@pytest.mark.asyncio
async def test_crawl_submits_seed_to_peanut_index():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "status": "ok", "visited": 4, "indexed": 3,
            "sitemapPagesDiscovered": 2,
        })

    result = await make_client(handler).crawl("https://example.org", max_pages=4)

    assert seen["path"] == "/index/crawl"
    assert seen["body"] == {"url": "https://example.org", "maxPages": 4}
    assert result["indexed"] == 3


@pytest.mark.asyncio
async def test_search_rejects_unconfigured_gateway():
    with pytest.raises(PeanutBrowsingError, match="not configured"):
        await PeanutBrowsingClient(base_url="", api_key="").search("query")


@pytest.mark.asyncio
async def test_search_rejects_invalid_result_urls():
    def handler(request):
        return httpx.Response(200, json={
            "status": "ok",
            "results": [
                {"title": "unsafe", "url": "file:///etc/passwd"},
                {"title": "safe", "url": "https://example.org"},
            ],
        })

    result = await make_client(handler).search("query")
    assert [item["title"] for item in result["results"]] == ["safe"]


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin",
    "http://10.0.0.5/",
    "file:///etc/passwd",
    "https://user:pass@example.org/",
])
@pytest.mark.asyncio
async def test_crawl_rejects_non_public_or_credential_urls(url):
    with pytest.raises(ValueError):
        await make_client(lambda request: httpx.Response(200, json={"status": "ok"})).crawl(url)


@pytest.mark.asyncio
async def test_search_rejects_http_gateway_outside_loopback():
    client = PeanutBrowsingClient(base_url="http://peanut.example", api_key="test-key")
    with pytest.raises(PeanutBrowsingError, match="HTTPS"):
        await client.search("query")


def test_peanut_browsing_crawl_is_privileged():
    assert "peanut_browsing_crawl" in NON_ADMIN_BLOCKED_TOOLS
