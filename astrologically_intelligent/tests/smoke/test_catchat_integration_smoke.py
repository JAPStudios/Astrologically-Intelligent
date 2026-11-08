"""CatChat's delegated chat-token contract against the running application.

CatChat creates a session with form-encoded endpoint_id/model fields, then
sends JSON {message, session} to /api/chat. Exercise those exact HTTP shapes
against a real Astrologically Intelligent instance and its deterministic
smoke provider; no external model credentials or network service are used.
"""
from __future__ import annotations

import httpx
from tests.smoke.stub_provider import MODEL_PRIMARY, reply_for


def test_catchat_chat_token_creates_session_and_completes_message(
    client, stub_endpoint, stub_provider
):
    """A chat-scoped bearer token can use CatChat's session/chat request flow."""
    token_response = client.post(
        "/api/tokens",
        data={"name": "catchat-integration-smoke", "scopes": "chat"},
    )
    assert token_response.status_code == 200, token_response.text
    token = token_response.json()
    assert token["scopes"] == ["chat"]

    session_id = None
    delegated = httpx.Client(
        base_url=str(client.base_url),
        headers={"Authorization": "Bearer " + token["token"]},
        timeout=120.0,
    )
    try:
        created = delegated.post(
            "/api/session",
            data={
                "name": "CatChat integration smoke",
                "endpoint_id": stub_endpoint,
                "model": MODEL_PRIMARY,
            },
        )
        assert created.status_code == 200, created.text
        session = created.json()
        session_id = session["id"]
        assert session["model"] == MODEL_PRIMARY

        prompt = "CatChat integration smoke message"
        completed = delegated.post(
            "/api/chat",
            json={"message": prompt, "session": session_id},
        )
        assert completed.status_code == 200, completed.text
        body = completed.json()
        assert body["response"] == reply_for(MODEL_PRIMARY)
        assert body["model"] == MODEL_PRIMARY
        assert any(prompt in seen for seen in stub_provider.recorder.prompts())
    finally:
        delegated.close()
        if session_id:
            deleted_session = client.delete(f"/api/session/{session_id}")
            assert deleted_session.status_code in (200, 204), deleted_session.text
        deleted_token = client.delete(f"/api/tokens/{token['id']}")
        assert deleted_token.status_code == 200, deleted_token.text


def test_non_chat_token_cannot_create_catchat_session_or_send_chat(
    client, stub_endpoint
):
    """A token with unrelated scope cannot use CatChat's chat endpoints."""
    token_response = client.post(
        "/api/tokens",
        data={"name": "catchat-wrong-scope-smoke", "scopes": "cookbook:read"},
    )
    assert token_response.status_code == 200, token_response.text
    token = token_response.json()
    assert "chat" not in token["scopes"]

    delegated = httpx.Client(
        base_url=str(client.base_url),
        headers={"Authorization": "Bearer " + token["token"]},
        timeout=30.0,
    )
    try:
        created = delegated.post(
            "/api/session",
            data={
                "name": "CatChat wrong-scope smoke",
                "endpoint_id": stub_endpoint,
                "model": MODEL_PRIMARY,
            },
        )
        assert created.status_code == 403, created.text

        rejected = delegated.post(
            "/api/chat",
            json={"message": "must be denied", "session": "not-a-session"},
        )
        assert rejected.status_code == 403, rejected.text
    finally:
        delegated.close()
        deleted_token = client.delete(f"/api/tokens/{token['id']}")
        assert deleted_token.status_code == 200, deleted_token.text
