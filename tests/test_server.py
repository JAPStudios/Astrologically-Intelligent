import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from astrologically_intelligent.runtime import AgentRuntime
from astrologically_intelligent.storage import Store
from astrologically_intelligent.server import make_handler


class HistoryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.runtime = AgentRuntime(provider=object(), store=self.store)
        self.store.add_message("session-1", "user", "First message")
        self.store.add_message("session-1", "assistant", "First reply")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.runtime, "test-token"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.runtime.close()

    def request(self, path, token="test-token"):
        request = urllib.request.Request(self.url + path)
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        return urllib.request.urlopen(request, timeout=3)

    def test_history_returns_session_messages_in_chronological_order(self):
        with self.request("/v1/history?session_id=session-1") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["messages"], [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First reply"},
        ])

    def test_health_remains_public(self):
        with urllib.request.urlopen(self.url + "/health", timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["status"], "ok")

    def test_history_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/history?session_id=session-1", token="")
        self.assertEqual(raised.exception.code, 401)

    def test_history_rejects_missing_session_and_invalid_limits(self):
        for path in ("/v1/history", "/v1/history?session_id=session-1&limit=0",
                     "/v1/history?session_id=session-1&limit=201",
                     "/v1/history?session_id=session-1&limit=invalid"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request(path)
            self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
