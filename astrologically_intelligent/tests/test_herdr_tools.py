import json
import subprocess
from unittest.mock import patch

import pytest

from src.tool_security import NON_ADMIN_BLOCKED_TOOLS

from src.agent_tools.herdr_tools import (
    HerdrAgentExplainTool,
    HerdrAgentGetTool,
    HerdrAgentListTool,
    HerdrAgentReadTool,
)


@pytest.mark.asyncio
async def test_herdr_tools_refuse_to_run_outside_herdr(monkeypatch):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    with patch("src.agent_tools.herdr_tools.subprocess.run") as run:
        result = await HerdrAgentListTool().execute("")
    assert "HERDR_ENV=1" in result["error"]
    run.assert_not_called()


@pytest.mark.asyncio
async def test_herdr_agent_list_uses_json_cli_without_a_shell(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr("src.agent_tools.herdr_tools.shutil.which", lambda _name: "/usr/bin/herdr")
    completed = subprocess.CompletedProcess(
        args=["herdr", "agent", "list", "--json"],
        returncode=0,
        stdout=json.dumps({"agents": []}),
        stderr="",
    )
    with patch("src.agent_tools.herdr_tools.subprocess.run", return_value=completed) as run:
        result = await HerdrAgentListTool().execute("")
    assert result["output"] == {"agents": []}
    args, kwargs = run.call_args
    assert args[0] == ["herdr", "agent", "list", "--json"]
    assert kwargs["shell"] is False


@pytest.mark.asyncio
async def test_herdr_agent_read_validates_arguments_and_uses_documented_source(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr("src.agent_tools.herdr_tools.shutil.which", lambda _name: "/usr/bin/herdr")
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="Agent is waiting for input",
        stderr="",
    )
    with patch("src.agent_tools.herdr_tools.subprocess.run", return_value=completed) as run:
        result = await HerdrAgentReadTool().execute(json.dumps({
            "target": "w1:p2",
            "source": "recent-unwrapped",
            "lines": 120,
            "format": "text",
        }))
    assert result["output"] == "Agent is waiting for input"
    assert run.call_args.args[0] == [
        "herdr", "agent", "read", "w1:p2",
        "--source", "recent-unwrapped", "--lines", "120", "--format", "text",
    ]


@pytest.mark.asyncio
async def test_herdr_agent_get_and_explain_use_agent_identifiers(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr("src.agent_tools.herdr_tools.shutil.which", lambda _name: "/usr/bin/herdr")
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"state":"idle"}', stderr="")
    with patch("src.agent_tools.herdr_tools.subprocess.run", return_value=completed) as run:
        get_result = await HerdrAgentGetTool().execute('{"target":"reviewer"}')
        explain_result = await HerdrAgentExplainTool().execute('{"target":"w1:p2"}')
    assert get_result["output"] == {"state": "idle"}
    assert explain_result["output"] == {"state": "idle"}
    assert run.call_args_list[0].args[0] == ["herdr", "agent", "get", "reviewer", "--json"]
    assert run.call_args_list[1].args[0] == ["herdr", "agent", "explain", "w1:p2", "--json"]


@pytest.mark.asyncio
async def test_herdr_agent_get_rejects_option_injection(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    with patch("src.agent_tools.herdr_tools.subprocess.run") as run:
        result = await HerdrAgentGetTool().execute('{"target":"--machine"}')
    assert "agent name or pane ID" in result["error"]
    run.assert_not_called()


@pytest.mark.asyncio
async def test_herdr_agent_read_rejects_invalid_limits(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    with patch("src.agent_tools.herdr_tools.subprocess.run") as run:
        result = await HerdrAgentReadTool().execute('{"target":"reviewer","lines":0}')
    assert "lines must be" in result["error"]
    run.assert_not_called()

def test_herdr_inspection_tools_are_privileged():
    assert {
        "herdr_agent_list",
        "herdr_agent_get",
        "herdr_agent_read",
        "herdr_agent_explain",
    } <= NON_ADMIN_BLOCKED_TOOLS
