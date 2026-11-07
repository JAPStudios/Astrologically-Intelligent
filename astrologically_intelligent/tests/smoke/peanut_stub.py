"""Loopback Peanut Browsing gateway for deterministic agent-tool smoke tests."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

BIND_HOST = "127.0.0.1"
API_KEY = "odysseus-smoke-peanut-key"
RESULT_MARKER = "ODYSSEUS-SMOKE-PEANUT-RESULT"


class PeanutIndexStub:
    def __init__(self):
        self._lock = threading.Lock()
        self._calls = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send_json(self, status, body):
                raw = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _authorized(self):
                if self.headers.get("X-API-Key") == API_KEY:
                    return True
                self._send_json(401, {"status": "error", "error": "unauthorized"})
                return False

            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == "/__smoke__/calls":
                    with owner._lock:
                        calls = list(owner._calls)
                    self._send_json(200, {"calls": calls})
                    return
                if parsed.path != "/index/search":
                    self._send_json(404, {"status": "error", "error": "not found"})
                    return
                if not self._authorized():
                    return
                query = parse_qs(parsed.query).get("q", [""])[0]
                with owner._lock:
                    owner._calls.append({"method": "GET", "query": query})
                self._send_json(200, {
                    "status": "ok",
                    "results": [{
                        "title": RESULT_MARKER,
                        "url": "https://example.com/peanut-smoke",
                        "snippet": "Deterministic indexed result from the Peanut Browsing smoke gateway.",
                        "score": 0.987,
                    }],
                    "totalResults": 1,
                })

            def do_POST(self):
                parsed = urlsplit(self.path)
                if parsed.path != "/index/crawl":
                    self._send_json(404, {"status": "error", "error": "not found"})
                    return
                if not self._authorized():
                    return
                length = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    body = {}
                with owner._lock:
                    owner._calls.append({"method": "POST", "body": body})
                self._send_json(200, {
                    "status": "ok",
                    "visited": 1,
                    "indexed": 1,
                    "sitemapPagesDiscovered": 0,
                })

        self._server = ThreadingHTTPServer((BIND_HOST, 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self):
        return f"http://{BIND_HOST}:{self._server.server_address[1]}"

    @property
    def api_key(self):
        return API_KEY

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)