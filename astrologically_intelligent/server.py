"""Minimal JSON HTTP API; binds to loopback unless explicitly configured otherwise."""
from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .runtime import AgentRuntime


def _valid_session_id(value: object) -> bool:
    """Apply the same bounded ASCII identifier contract to every session route."""
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and all((char.isascii() and char.isalnum()) or char in "_-" for char in value)
    )


def make_handler(runtime: AgentRuntime, token: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self,status:int,payload:dict):
            body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            return not token or hmac.compare_digest(
                self.headers.get("Authorization",""), f"Bearer {token}"
            )

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                return self._send(200,{"status":"ok","service":"astrologically-intelligent"})
            if parsed.path not in {"/v1/history", "/v1/sessions"}:
                return self._send(404,{"error":"not_found"})
            if not self._authorized():
                return self._send(401,{"error":"unauthorized"})
            query = parse_qs(parsed.query, keep_blank_values=True)
            if parsed.path == "/v1/sessions":
                try:
                    limit = int(query.get("limit", ["50"])[0])
                except (TypeError, ValueError):
                    return self._send(400,{"error":"invalid_limit"})
                if not 1 <= limit <= 100:
                    return self._send(400,{"error":"invalid_limit"})
                return self._send(200, {"sessions": runtime.store.list_sessions(limit)})
            session_id = query.get("session_id", [""])[0]
            if not _valid_session_id(session_id):
                return self._send(400,{"error":"invalid_session_id"})
            try:
                limit = int(query.get("limit", ["40"])[0])
            except (TypeError, ValueError):
                return self._send(400,{"error":"invalid_limit"})
            if not 1 <= limit <= 200:
                return self._send(400,{"error":"invalid_limit"})
            return self._send(200, {
                "session_id": session_id,
                "messages": runtime.store.history(session_id, limit),
            })

        def do_DELETE(self):
            parsed = urlsplit(self.path)
            prefix = "/v1/sessions/"
            if not parsed.path.startswith(prefix):
                return self._send(404,{"error":"not_found"})
            if not self._authorized():
                return self._send(401,{"error":"unauthorized"})
            session_id = parsed.path[len(prefix):]
            if not _valid_session_id(session_id):
                return self._send(400,{"error":"invalid_session_id"})
            if not runtime.store.delete_session(session_id):
                return self._send(404,{"error":"session_not_found"})
            return self._send(200,{"deleted":True,"session_id":session_id})

        def do_POST(self):
            if self.path!="/v1/chat": return self._send(404,{"error":"not_found"})
            if not self._authorized():
                return self._send(401,{"error":"unauthorized"})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<1 or length>1_000_000: return self._send(413,{"error":"invalid_body_size"})
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict): return self._send(400,{"error":"body_must_be_object"})
                session_id = data.get("session_id")
                if session_id is not None and not _valid_session_id(session_id):
                    return self._send(400,{"error":"invalid_session_id"})
                result=runtime.chat(data.get("message"),session_id)
                self._send(200,result)
            except (ValueError,json.JSONDecodeError) as exc: self._send(400,{"error":str(exc)})
            except RuntimeError as exc: self._send(502,{"error":str(exc)})

        def log_message(self,fmt,*args): return
    return Handler


def serve():
    host=os.getenv("ASTRO_AI_HOST","127.0.0.1")
    port=int(os.getenv("ASTRO_AI_PORT","8765"))
    token=os.getenv("ASTRO_AI_API_TOKEN","")
    if host not in {"127.0.0.1","::1","localhost"} and len(token)<24:
        raise RuntimeError("Non-loopback binding requires ASTRO_AI_API_TOKEN of at least 24 characters")
    runtime=AgentRuntime()
    server=ThreadingHTTPServer((host,port),make_handler(runtime,token))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        runtime.close()


if __name__=="__main__":
    serve()
