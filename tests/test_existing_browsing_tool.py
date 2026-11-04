import unittest
from unittest.mock import Mock, patch

from astrologically_intelligent.tools import _open_existing_browsing, _search_existing_browsing


class ExistingBrowsingToolTests(unittest.TestCase):
    def test_delegates_to_existing_search_and_returns_context_sources(self):
        search = Mock(return_value=("Research context", [{"title": "Source", "url": "https://example.org"}]))
        with patch("astrologically_intelligent.tools._load_existing_search", return_value=search):
            result = _search_existing_browsing("  test query  ", max_pages=4, time_filter="week")

        search.assert_called_once_with(
            "test query", max_pages=4, time_filter="week", return_sources=True
        )
        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["context"], "Research context")
        self.assertEqual(result["sources"][0]["url"], "https://example.org")

    def test_rejects_invalid_page_limit(self):
        with self.assertRaises(ValueError):
            _search_existing_browsing("query", max_pages=11)

    def test_rejects_invalid_time_filter(self):
        with self.assertRaises(ValueError):
            _search_existing_browsing("query", time_filter="forever")


    def test_opens_page_through_existing_extractor(self):
        page = {"url": "https://example.org/page", "title": "Example",
                "content": "Extracted page text", "success": True,
                "meta_description": "Page description", "lists": [["one", "two"]],
                "tables": [], "code_blocks": []}
        fetch = Mock(return_value=page)
        with patch("astrologically_intelligent.tools._load_existing_page_fetcher", return_value=fetch):
            result = _open_existing_browsing("https://example.org/page")
        fetch.assert_called_once_with("https://example.org/page")
        self.assertEqual(result["title"], "Example")
        self.assertEqual(result["content"], "Extracted page text")
        self.assertTrue(result["success"])
        self.assertEqual(result["meta_description"], "Page description")

    def test_caps_extracted_page_content(self):
        page = {"url": "https://example.org", "content": "x" * 2000, "success": True}
        fetch = Mock(return_value=page)
        with patch("astrologically_intelligent.tools._load_existing_page_fetcher", return_value=fetch):
            result = _open_existing_browsing("https://example.org", max_chars=500)
        self.assertEqual(len(result["content"]), 500)
        self.assertTrue(result["truncated"])

    def test_rejects_non_public_url_shapes_before_fetch(self):
        for url in ("file:///etc/passwd", "https://user:pass@example.org",
                    "//example.org/path", "javascript:alert(1)"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    _open_existing_browsing(url)

    def test_rejects_unbounded_content_limit(self):
        with self.assertRaises(ValueError):
            _open_existing_browsing("https://example.org", max_chars=50000)


    def test_deep_research_uses_active_openai_compatible_model(self):
        from types import SimpleNamespace
        from astrologically_intelligent.tools import _run_deep_research
        provider = type("OpenAICompatibleProvider", (), {})()
        provider.config = SimpleNamespace(base_url="https://model.example/v1", model="model-x", api_key="secret")
        fake_result = SimpleNamespace(query="topic", summary="Report", sources=[], duration_seconds=2.5, tokens_used=0)
        async def fake_research(*args, **kwargs):
            return fake_result
        with patch("astrologically_intelligent.services.research.service.ResearchService.research", new=fake_research):
            result = _run_deep_research(provider, "topic", 60)
        self.assertEqual(result["report"], "Report")
        self.assertEqual(result["query"], "topic")

    def test_deep_research_marks_basic_search_fallback(self):
        from types import SimpleNamespace
        from astrologically_intelligent.tools import _run_deep_research
        provider = type("OpenAICompatibleProvider", (), {})()
        provider.config = SimpleNamespace(base_url="https://model.example/v1", model="model-x", api_key="secret")
        fake_result = SimpleNamespace(
            query="topic", summary="## Research Failed - Basic Search Fallback\\n\\nSearch results",
            sources=[], duration_seconds=1.0, tokens_used=0,
        )
        async def fake_research(*args, **kwargs):
            return fake_result
        with patch("astrologically_intelligent.services.research.service.ResearchService.research", new=fake_research):
            result = _run_deep_research(provider, "topic", 60)
        self.assertEqual(result["status"], "fallback")
        self.assertIn("Search results", result["report"])

    def test_deep_research_rejects_complete_engine_failure(self):
        from types import SimpleNamespace
        from astrologically_intelligent.tools import _run_deep_research
        provider = type("OpenAICompatibleProvider", (), {})()
        provider.config = SimpleNamespace(base_url="https://model.example/v1", model="model-x", api_key="secret")
        fake_result = SimpleNamespace(
            query="topic", summary="## Complete Research Failure\\n\\nNo result",
            sources=[], duration_seconds=1.0, tokens_used=0,
        )
        async def fake_research(*args, **kwargs):
            return fake_result
        with patch("astrologically_intelligent.services.research.service.ResearchService.research", new=fake_research):
            with self.assertRaisesRegex(RuntimeError, "could not produce"):
                _run_deep_research(provider, "topic", 60)

    def test_deep_research_rejects_invalid_time_budget(self):
        from astrologically_intelligent.tools import _run_deep_research
        with self.assertRaises(ValueError):
            _run_deep_research(None, "topic", 10)


if __name__ == "__main__":
    unittest.main()
