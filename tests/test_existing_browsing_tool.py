import unittest
from unittest.mock import Mock, patch

from astrologically_intelligent.tools import _search_existing_browsing


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


if __name__ == "__main__":
    unittest.main()
