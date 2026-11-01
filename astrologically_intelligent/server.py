"""Minimal JSON HTTP API; binds to loopback unless explicitly configured otherwise."""
from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .runtime import AgentRuntime


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

        def do_GET(self):
            if self.path=="/health":
                return self._send(200,{"status":"ok","service":"astrologically-intelligent"})
            self._send(404,{"error":"not_found"})

        def do_POST(self):
            if self.path!="/v1/chat": return self._send(404,{"error":"not_found"})
            if token and not hmac.compare_digest(self.headers.get("Authorization",""),f"Bearer {token}"):
                return self._send(401,{"error":"unauthorized"})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<1 or length>1_000_000: return self._send(413,{"error":"invalid_body_size"})
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict): return self._send(400,{"error":"body_must_be_object"})
                result=runtime.chat(data.get("message"),data.get("session_id"))
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
