"""CLI contract tests for the full-application release smoke runner."""
import argparse
from types import SimpleNamespace

from tests.helpers.cli_loader import load_script


def test_no_chroma_flag_is_forwarded_to_the_isolated_app_boot(tmp_path, monkeypatch):
    smoke = load_script("odysseus-smoke")
    captured = {}

    class Dev:
        @staticmethod
        def read_state(_root):
            return None

        @staticmethod
        def running_app(_state):
            return None

    def fake_run(command, *, cwd, env, check):
        captured.update(command=command, cwd=cwd, env=env, check=check)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)
    args = argparse.Namespace(
        restart=False,
        no_boot=False,
        no_chroma=True,
        venv="./venv",
    )

    started, note = smoke.boot(Dev(), tmp_path, args)

    assert started is True
    assert note == ""
    assert captured["command"] == [
        smoke.sys.executable,
        str(smoke.SCRIPTS_DIR / smoke.DEV_SCRIPT),
        "up",
        "--venv",
        "./venv",
        "--no-chroma",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["env"][smoke.EMAIL_FIXTURE_ENV] == "1"
    assert captured["check"] is False


def test_smoke_parser_exposes_no_chroma_mode():
    smoke = load_script("odysseus-smoke")

    args = smoke.build_parser().parse_args(["--no-chroma"])

    assert args.no_chroma is True
