import io
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch

from astrologically_intelligent.providers import _post_json


class ProviderRetryTests(unittest.TestCase):
    def _http_error(self, status, retry_after=None):
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)
        return urllib.error.HTTPError(
            "https://provider.invalid/chat", status, "provider error",
            headers, io.BytesIO(b"untrusted response body"),
        )

    def test_retries_rate_limit_then_returns_json(self):
        response = io.BytesIO(b'{"choices": []}')
        with patch("urllib.request.urlopen", side_effect=[
            self._http_error(429, "1"), response
        ]) as request, patch("time.sleep") as sleep:
            result = _post_json(
                "https://provider.invalid/chat",
                {"model": "example", "messages": []}, {}, 10,
            )
        self.assertEqual(result, {"choices": []})
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(1.0)
        self.assertEqual(request.call_args_list[0].args[0].data,
                         request.call_args_list[1].args[0].data)

    def test_does_not_retry_authentication_failures(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(401)) as request, \
             patch("time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                _post_json("https://provider.invalid/chat", {}, {}, 10)
        request.assert_called_once()
        sleep.assert_not_called()

    def test_stops_after_four_transient_http_failures(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(503)) as request, \
             patch("time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                _post_json("https://provider.invalid/chat", {}, {}, 10)
        self.assertEqual(request.call_count, 4)
        self.assertEqual(sleep.call_count, 3)

    def test_retries_connection_errors_with_bounded_backoff(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")) as request, \
             patch("time.sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "Provider connection failed"):
                _post_json("https://provider.invalid/chat", {}, {}, 10)
        self.assertEqual(request.call_count, 4)
        self.assertEqual([call.args[0] for call in sleep.call_args_list],
                         [0.25, 0.5, 1.0])


if __name__ == "__main__":
    unittest.main()
