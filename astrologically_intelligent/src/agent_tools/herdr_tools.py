"""Read-only access to the current Herdr agent runtime.

Herdr's own skill requires execution inside a Herdr-managed pane. This module
enforces that boundary before invoking the CLI and never uses a shell.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess


_TARGET = re.compile(r"^(?:[a-z][a-z0-9_-]{0,31}|w[0-9]+:p[0-9]+)$")


class HerdrRuntimeTool:
    def __init__(self, *, timeout: float = 15.0):
        self.timeout = timeout

    def _available(self) -> str | None:
        if os.getenv("HERDR_ENV") != "1":
            return "Herdr controls are available only when this agent is running inside a Herdr-managed pane (HERDR_ENV=1)."
        binary = shutil.which("herdr")
        if not binary:
            return "HERDR_ENV=1 is set, but the Herdr CLI is not available in PATH."
        return None

    async def _run(self, args: list[str], *, timeout: float | None = None, json_output: bool = True) -> dict:
        unavailable = self._available()
        if unavailable:
            return {"error": unavailable, "exit_code": 1}
        command = ["herdr", *args]
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return {"error": "Herdr command timed out.", "exit_code": 124}
        except OSError as exc:
            return {"error": f"Could not execute Herdr: {type(exc).__name__}.", "exit_code": 1}
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode != 0:
            return {
                "error": stderr[:4000] or f"Herdr exited with status {result.returncode}.",
                "exit_code": result.returncode,
            }
        if not json_output:
            return {"output": stdout[:16000], "exit_code": 0}
        try:
            payload = json.loads(stdout)
        except (TypeError, ValueError):
            return {"error": "Herdr did not return valid JSON.", "output": stdout[:4000], "exit_code": 1}
        return {"output": payload, "exit_code": 0}


class HerdrAgentListTool(HerdrRuntimeTool):
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        return await self._run(["agent", "list", "--json"])


class HerdrAgentGetTool(HerdrRuntimeTool):
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        try:
            args = json.loads(content or "{}")
        except (TypeError, ValueError):
            return {"error": "Arguments must be valid JSON.", "exit_code": 1}
        target = args.get("target") if isinstance(args, dict) else None
        if not isinstance(target, str) or not _TARGET.fullmatch(target.strip()):
            return {"error": "target must be a Herdr agent name or pane ID such as reviewer or w1:p2.", "exit_code": 1}
        return await self._run(["agent", "get", target.strip(), "--json"])


class HerdrAgentReadTool(HerdrRuntimeTool):
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        try:
            args = json.loads(content or "{}")
        except (TypeError, ValueError):
            return {"error": "Arguments must be valid JSON.", "exit_code": 1}
        if not isinstance(args, dict):
            return {"error": "Arguments must be a JSON object.", "exit_code": 1}
        target = args.get("target")
        source = args.get("source", "recent-unwrapped")
        lines = args.get("lines", 120)
        output_format = args.get("format", "text")
        if not isinstance(target, str) or not target.strip() or len(target) > 128 or any(ord(ch) < 32 for ch in target):
            return {"error": "target must be a non-empty agent name or pane ID of at most 128 characters.", "exit_code": 1}
        if source not in {"visible", "recent", "recent-unwrapped", "detection"}:
            return {"error": "source must be visible, recent, recent-unwrapped or detection.", "exit_code": 1}
        if isinstance(lines, bool) or not isinstance(lines, int) or not 1 <= lines <= 500:
            return {"error": "lines must be an integer from 1 to 500.", "exit_code": 1}
        if output_format not in {"text", "ansi"}:
            return {"error": "format must be text or ansi.", "exit_code": 1}
        return await self._run(
            ["agent", "read", target.strip(), "--source", source, "--lines", str(lines), "--format", output_format],
            json_output=False,
        )


class HerdrAgentExplainTool(HerdrRuntimeTool):
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        try:
            args = json.loads(content or "{}")
        except (TypeError, ValueError):
            return {"error": "Arguments must be valid JSON.", "exit_code": 1}
        target = args.get("target") if isinstance(args, dict) else None
        if not isinstance(target, str) or not target.strip() or len(target) > 128 or any(ord(ch) < 32 for ch in target):
            return {"error": "target must be a non-empty agent name or pane ID of at most 128 characters.", "exit_code": 1}
        return await self._run(["agent", "explain", target.strip(), "--json"])
