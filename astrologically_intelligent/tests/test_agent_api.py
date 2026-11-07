import tempfile
import unittest
from unittest.mock import patch
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agent_api import AgentRuntimeRegistry, create_agent_api_router


class FakeRuntime:
    def __init__(self, store):
        self.store = store

    def chat(self, message, session_id=None):
        session_id = session_id or "new-session"
        self.store.add_message(session_id, "user", message)
        self.store.add_message(session_id, "assistant", "Received: " + message)
        return {"session_id": session_id, "response": "Received: " + message}


class FakeAuthManager:
    def is_admin(self, username):
        return username in {"admin", "alice", "bob"}


class AgentApiTests(unittest.TestCase):
    def make_app(self, registry, auth_enabled=False):
        app = FastAPI()
        app.state.auth_manager = FakeAuthManager()

        @app.middleware("http")
        async def test_identity(request, call_next):
            owner = request.headers.get("X-Test-Owner")
            if owner:
                request.state.current_user = owner
            if request.headers.get("X-Test-Remote") == "true":
                request.scope["client"] = ("10.0.2.2", 12345)
            if request.headers.get("X-Test-Api-Token") == "true":
                request.state.api_token = True
                request.state.api_token_owner = owner
                request.state.api_token_scopes = [
                    value for value in request.headers.get("X-Test-Scopes", "").split(",") if value
                ]
            return await call_next(request)

        app.include_router(create_agent_api_router(registry, auth_enabled=auth_enabled))
        return app

    def test_chat_and_history_are_isolated_by_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AgentRuntimeRegistry(directory, runtime_factory=FakeRuntime)
            client = TestClient(self.make_app(registry, auth_enabled=True))
            alice_headers = {"X-Test-Owner": "alice"}
            bob_headers = {"X-Test-Owner": "bob"}
            alice = client.post("/v1/chat", headers=alice_headers, json={"message": "Alice note", "session_id": "shared"})
            self.assertEqual(alice.status_code, 200)
            bob = client.post("/v1/chat", headers=bob_headers, json={"message": "Bob note", "session_id": "shared"})
            self.assertEqual(bob.status_code, 200)
            alice_history = client.get("/v1/sessions/shared", headers=alice_headers)
            bob_history = client.get("/v1/sessions/shared", headers=bob_headers)
            self.assertEqual(alice_history.status_code, 200)
            self.assertEqual(bob_history.status_code, 200)
            self.assertEqual([item["content"] for item in alice_history.json()["messages"]], [
                "Alice note", "Received: Alice note"
            ])
            self.assertEqual([item["content"] for item in bob_history.json()["messages"]], [
                "Bob note", "Received: Bob note"
            ])
            registry.close()

    def test_chat_token_scope_and_admin_authorization_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AgentRuntimeRegistry(directory, runtime_factory=FakeRuntime)
            client = TestClient(self.make_app(registry, auth_enabled=True))
            no_scope = client.post("/v1/chat", headers={
                "X-Test-Owner": "admin", "X-Test-Api-Token": "true",
                "X-Test-Scopes": "documents:read",
            }, json={"message": "hello"})
            self.assertEqual(no_scope.status_code, 403)
            non_admin = client.post("/v1/chat", headers={
                "X-Test-Owner": "member",
            }, json={"message": "hello"})
            self.assertEqual(non_admin.status_code, 403)
            valid = client.post("/v1/chat", headers={
                "X-Test-Owner": "admin", "X-Test-Api-Token": "true",
                "X-Test-Scopes": "chat",
            }, json={"message": "hello", "session_id": "valid-1"})
            self.assertEqual(valid.status_code, 200)
            registry.close()

    def test_invalid_session_ids_and_malformed_chat_payloads_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AgentRuntimeRegistry(directory, runtime_factory=FakeRuntime)
            client = TestClient(self.make_app(registry, auth_enabled=False))
            invalid = client.get("/v1/sessions/../private")
            self.assertIn(invalid.status_code, (400, 404))
            empty = client.post("/v1/chat", json={"message": " "})
            self.assertEqual(empty.status_code, 400)
            registry.close()

    def test_emulator_bridge_requires_a_bearer_token_when_auth_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AgentRuntimeRegistry(directory, runtime_factory=FakeRuntime)
            client = TestClient(self.make_app(registry, auth_enabled=False))
            remote = {"X-Test-Remote": "true"}
            denied = client.post("/v1/chat", headers=remote, json={"message": "hello"})
            self.assertEqual(denied.status_code, 401)
            with patch.dict(os.environ, {"ASTRO_AI_API_TOKEN": "local-agent-token"}):
                allowed = client.post(
                    "/v1/chat",
                    headers={**remote, "Authorization": "Bearer local-agent-token"},
                    json={"message": "hello"},
                )
            self.assertEqual(allowed.status_code, 200)
            registry.close()

    def test_registry_creates_distinct_databases_for_each_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AgentRuntimeRegistry(directory, runtime_factory=FakeRuntime)
            alice, _ = registry.runtime("alice")
            bob, _ = registry.runtime("bob")
            self.assertIsNot(alice.store, bob.store)
            self.assertNotEqual(alice.store.path, bob.store.path)
            registry.close()


if __name__ == "__main__":
    unittest.main()
