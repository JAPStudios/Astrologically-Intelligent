"""Exercise Peanut Browsing through the full chat-to-tool-to-gateway path."""
from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from tests.smoke.stub_provider import (
    PEANUT_RESULT_MARKER,
    PEANUT_SEARCH_FINAL,
    PEANUT_SEARCH_PROMPT,
    PEANUT_SEARCH_QUERY,
)
from src.agent_tools.peanut_tools import PeanutCrawlTool

PEANUT_CRAWL_URL = "https://example.com/odysseus-smoke-peanut"

CHAT_PATH = "/api/chat"


def _gateway_calls():
    if os.getenv("ODYSSEUS_PEANUT_SMOKE_STUB_ENABLED") != "1":
        pytest.skip("the smoke runner did not boot the local Peanut Browsing gateway fixture")
    base_url = os.getenv("PEANUT_SEARCH_API_URL", "").rstrip("/")
    if not base_url:
        pytest.skip("PEANUT_SEARCH_API_URL is not available in this smoke process")
    response = httpx.get(f"{base_url}/__smoke__/calls", timeout=10)
    assert response.status_code == 200, response.text
    return response.json().get("calls") or []


def _assert_tool_result_reached_follow_up(stub_provider, tool_name, marker):
    calls = stub_provider.recorder.calls
    assert any(
        any((tool.get("function") or {}).get("name") == tool_name for tool in call.get("tools") or [])
        for call in calls
    ), f"{tool_name} was not offered to the model"
    assert any(
        message.get("role") == "tool" and marker in str(message.get("content") or "")
        for call in calls
        for message in call.get("messages") or []
    ), f"{tool_name} result did not reach the model follow-up"


def test_peanut_search_completes_a_native_agent_tool_cycle(client, chat_session, stub_provider):
    _gateway_calls()
    stub_provider.recorder.clear()
    response = client.post(CHAT_PATH, json={
        "message": f"Search Peanut Browsing for {PEANUT_SEARCH_PROMPT}.",
        "session": chat_session,
        "allow_web_search": True,
    })
    assert response.status_code == 200, response.text
    assert response.json().get("response") == PEANUT_SEARCH_FINAL, response.json()
    _assert_tool_result_reached_follow_up(stub_provider, "web_search", PEANUT_RESULT_MARKER)
    calls = _gateway_calls()
    assert any(call.get("method") == "GET" and call.get("query") == PEANUT_SEARCH_QUERY for call in calls), calls


def test_peanut_crawl_tool_submits_a_public_url_to_the_gateway():
    _gateway_calls()
    result = asyncio.run(PeanutCrawlTool().execute(json.dumps({
        "url": PEANUT_CRAWL_URL,
        "max_pages": 1,
    })))
    assert result.get("exit_code") == 0, result
    assert "Peanut Browsing crawl completed." in result.get("output", ""), result
    calls = _gateway_calls()
    assert any(
        call.get("method") == "POST"
        and (call.get("body") or {}).get("url") == PEANUT_CRAWL_URL
        and (call.get("body") or {}).get("maxPages") == 1
        for call in calls
    ), calls