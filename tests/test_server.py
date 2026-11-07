import json
import http.client
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import quote
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from astrologically_intelligent.runtime import AgentRuntime
from astrologically_intelligent.storage import Store
from astrologically_intelligent.server import make_handler, serve


class HistoryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.runtime = AgentRuntime(provider=object(), store=self.store)
        self.store.add_message("session-1", "user", "First message")
        self.store.add_message("session-1", "assistant", "First reply")
        self.store.add_message("session-2", "user", "Another conversation")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.runtime, "test-token"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.runtime.close()

    def request(self, path, token="test-token", method="GET"):
        request = urllib.request.Request(self.url + path, method=method)
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

    def test_sessions_returns_recent_conversation_previews(self):
        with self.request("/v1/sessions") as response:
            payload = json.loads(response.read())
        self.assertEqual([item["session_id"] for item in payload["sessions"]],
                         ["session-2", "session-1"])
        self.assertEqual(payload["sessions"][0]["preview"], "Another conversation")
        self.assertEqual(payload["sessions"][1]["message_count"], 2)

    def test_sessions_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions", token="")
        self.assertEqual(raised.exception.code, 401)

    def test_sessions_rejects_invalid_limits(self):
        for path in ("/v1/sessions?limit=0", "/v1/sessions?limit=101",
                     "/v1/sessions?limit=invalid"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request(path)
            self.assertEqual(raised.exception.code, 400)

    def test_delete_removes_only_the_selected_conversation(self):
        with self.request("/v1/sessions/session-1", method="DELETE") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload, {"deleted": True, "session_id": "session-1"})
        with self.request("/v1/history?session_id=session-1") as response:
            self.assertEqual(json.loads(response.read())["messages"], [])
        with self.request("/v1/history?session_id=session-2") as response:
            self.assertEqual(len(json.loads(response.read())["messages"]), 1)

    def test_delete_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions/session-1", token="", method="DELETE")
        self.assertEqual(raised.exception.code, 401)

    def test_delete_reports_unknown_conversation(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/v1/sessions/missing", method="DELETE")
        self.assertEqual(raised.exception.code, 404)

    def test_health_remains_public(self):
        with urllib.request.urlopen(self.url + "/health", timeout=3) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["status"], "ok")

    def test_chat_rejects_invalid_session_identifiers_before_runtime(self):
        invalid_ids = (42, {}, "", "session/1", "session-é", "x" * 129)
        for session_id in invalid_ids:
            body = json.dumps({"message": "hello", "session_id": session_id}).encode("utf-8")
            request = urllib.request.Request(
                self.url + "/v1/chat",
                data=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with self.subTest(session_id=repr(session_id)):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(raised.exception.code, 400)
                self.assertEqual(
                    json.loads(raised.exception.read()),
                    {"error": "invalid_session_id"},
                )

    def test_history_rejects_invalid_session_identifiers(self):
        invalid_ids = ("", "session/1", "session-é", "session with spaces", "x" * 129)
        for session_id in invalid_ids:
            path = "/v1/history?session_id=" + quote(session_id, safe="")
            with self.subTest(session_id=repr(session_id)):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    self.request(path)
                self.assertEqual(raised.exception.code, 400)
                self.assertEqual(
                    json.loads(raised.exception.read()),
                    {"error": "invalid_session_id"},
                )

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


class FakeRuntime:
    def __init__(self):
        self.calls = []
        self.history_calls = []

    def chat(self, message, session_id=None):
        self.calls.append((message, session_id))
        return {"session_id": session_id or "new-session", "response": "Test response"}

    def history(self, session_id):
        self.history_calls.append(session_id)
        return [{"role": "user", "content": "Earlier question"},
                {"role": "assistant", "content": "Earlier answer"}]


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = None
        self.thread = None
        self.start_server("")

    def tearDown(self):
        self.stop_server()

    def stop_server(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.server = None
        self.thread = None

    def start_server(self, token):
        self.stop_server()
        self.runtime = FakeRuntime()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.runtime, token)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def get(self, path, headers=None):
        request = urllib.request.Request(
            self.base + path,
            headers=headers or {},
            method="GET",
        )
        return urllib.request.urlopen(request, timeout=3)

    def post(self, payload, headers=None):
        request = urllib.request.Request(
            self.base + "/v1/chat",
            data=payload,
            headers=headers or {},
            method="POST",
        )
        return urllib.request.urlopen(request, timeout=3)

    def test_http_chat_runs_agent_runtime_and_persists_session_history(self):
        self.stop_server()

        class DeterministicProvider:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools):
                self.calls.append(messages)
                return {"role": "assistant", "content": f"Runtime response {len(self.calls)}"}

        provider = DeterministicProvider()
        store = Store(":memory:")
        runtime = AgentRuntime(provider=provider, store=store)
        self.runtime = runtime
        self.server = ThreadingHTTPServer((
            "127.0.0.1", 0,
        ), make_handler(runtime, ""))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

        try:
            for expected in ("Runtime response 1", "Runtime response 2"):
                with self.post(
                    json.dumps({"message": "Continue", "session_id": "runtime-session"}).encode(),
                    {"Content-Type": "application/json"},
                ) as response:
                    body = json.loads(response.read())
                self.assertEqual(body["response"], expected)
                self.assertEqual(body["session_id"], "runtime-session")

            self.assertEqual(
                [message["role"] for message in store.history("runtime-session")],
                ["user", "assistant", "user", "assistant"],
            )
            self.assertEqual(
                [message["content"] for message in provider.calls[1][-3:]],
                ["Continue", "Runtime response 1", "Continue"],
            )
        finally:
            self.stop_server()
            runtime.close()

    def test_session_history_returns_display_messages(self):
        with self.get("/v1/sessions/session-1") as response:
            body = json.loads(response.read())
        self.assertEqual(body, {
            "session_id": "session-1",
            "messages": [
                {"role": "user", "content": "Earlier question"},
                {"role": "assistant", "content": "Earlier answer"},
            ],
        })
        self.assertEqual(self.runtime.history_calls, ["session-1"])

    def test_session_history_requires_valid_bearer_token_when_protected(self):
        token = "test-token-which-is-long-enough"
        self.start_server(token)
        for headers in ({}, {"Authorization": "Bearer wrong-token"}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.get("/v1/sessions/session-1", headers)
            self.assertEqual(error.exception.code, 401)
            self.assertEqual(json.loads(error.exception.read()), {"error": "unauthorized"})
        self.assertEqual(self.runtime.history_calls, [])

    def test_session_history_rejects_encoded_path_separators(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.get("/v1/sessions/invalid%2Fsession")
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(json.loads(error.exception.read()), {"error": "invalid_session_id"})

    def test_health_endpoint_returns_service_identity(self):
        with urllib.request.urlopen(self.base + "/health", timeout=3) as response:
            body = json.loads(response.read())
        self.assertEqual(body, {
            "status": "ok",
            "service": "astrologically-intelligent",
        })

    def test_chat_endpoint_routes_message_and_session(self):
        with self.post(
            json.dumps({"message": "Hello", "session_id": "session-1"}).encode(),
            {"Content-Type": "application/json"},
        ) as response:
            body = json.loads(response.read())
        self.assertEqual(body, {
            "session_id": "session-1",
            "response": "Test response",
        })
        self.assertEqual(self.runtime.calls, [("Hello", "session-1")])

    def test_protected_chat_rejects_missing_and_invalid_bearer_token(self):
        self.start_server("test-token-which-is-long-enough")
        for headers in ({}, {"Authorization": "Bearer wrong-token"}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post(b'{"message":"Hello"}', headers)
            self.assertEqual(error.exception.code, 401)
            self.assertEqual(
                json.loads(error.exception.read()), {"error": "unauthorized"}
            )
        self.assertEqual(self.runtime.calls, [])

    def test_protected_chat_accepts_valid_bearer_token(self):
        token = "test-token-which-is-long-enough"
        self.start_server(token)
        with self.post(
            b'{"message":"Hello","session_id":"protected-session"}',
            {"Authorization": f"Bearer {token}"},
        ) as response:
            body = json.loads(response.read())
        self.assertEqual(body["response"], "Test response")
        self.assertEqual(self.runtime.calls, [("Hello", "protected-session")])

    def test_chat_rejects_invalid_json_and_oversized_body(self):
        with self.assertRaises(urllib.error.HTTPError) as malformed_error:
            self.post(b"{")
        self.assertEqual(malformed_error.exception.code, 400)

        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        try:
            connection.putrequest("POST", "/v1/chat")
            connection.putheader("Content-Length", "1000001")
            connection.endheaders()
            oversized_response = connection.getresponse()
            self.assertEqual(oversized_response.status, 413)
            oversized_response.read()
        finally:
            connection.close()

    def test_non_loopback_server_requires_long_bearer_token(self):
        with patch.dict("os.environ", {
            "ASTRO_AI_HOST": "0.0.0.0",
            "ASTRO_AI_PORT": "8765",
            "ASTRO_AI_API_TOKEN": "too-short",
        }, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "at least 24 characters"
            ):
                serve()


if __name__ == "__main__":
    unittest.main()
