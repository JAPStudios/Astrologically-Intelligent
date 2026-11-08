import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_assembler():
    app_root = Path(__file__).resolve().parents[1]
    script = app_root / "scripts" / "assemble_sft_clean_corpus.py"
    spec = importlib.util.spec_from_file_location("assemble_sft_clean_corpus_under_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _run_main(monkeypatch, module, trace, verdicts, output, report, *repairs):
    argv = [
        "assemble_sft_clean_corpus.py",
        "--trace", str(trace),
        "--verdicts", str(verdicts),
        "--out-trace", str(output),
        "--report", str(report),
    ]
    for repair in repairs:
        argv.extend(["--repairs", str(repair)])
    monkeypatch.setattr(sys, "argv", argv)
    module.main()


def _valid_inputs(tmp_path):
    trace = tmp_path / "trace.jsonl"
    verdicts = tmp_path / "verdicts.jsonl"
    output = tmp_path / "clean.jsonl"
    report = tmp_path / "report.json"
    _write_jsonl(trace, [{"session_id": "session-a", "user": "question", "assistant": "answer"}])
    _write_jsonl(verdicts, [{"session_id": "session-a", "verdict": "keep"}])
    return trace, verdicts, output, report


def test_assembler_rejects_duplicate_verdicts(tmp_path, monkeypatch):
    module = _load_assembler()
    trace, verdicts, output, report = _valid_inputs(tmp_path)
    _write_jsonl(verdicts, [
        {"session_id": "session-a", "verdict": "keep"},
        {"session_id": "session-a", "verdict": "exclude"},
    ])

    with pytest.raises(ValueError, match="duplicate verdict"):
        _run_main(monkeypatch, module, trace, verdicts, output, report)


def test_assembler_rejects_verdict_for_unknown_session(tmp_path, monkeypatch):
    module = _load_assembler()
    trace, verdicts, output, report = _valid_inputs(tmp_path)
    _write_jsonl(verdicts, [{"session_id": "unknown", "verdict": "keep"}])

    with pytest.raises(ValueError, match="unknown source session"):
        _run_main(monkeypatch, module, trace, verdicts, output, report)


def test_assembler_rejects_unknown_verdict_value(tmp_path, monkeypatch):
    module = _load_assembler()
    trace, verdicts, output, report = _valid_inputs(tmp_path)
    _write_jsonl(verdicts, [{"session_id": "session-a", "verdict": "maybe"}])

    with pytest.raises(ValueError, match="unsupported verdict"):
        _run_main(monkeypatch, module, trace, verdicts, output, report)


def test_assembler_refuses_to_overwrite_input_trace(tmp_path, monkeypatch):
    module = _load_assembler()
    trace, verdicts, output, report = _valid_inputs(tmp_path)

    with pytest.raises(ValueError, match="output paths"):
        _run_main(monkeypatch, module, trace, verdicts, trace, report)


def test_assembler_rejects_malformed_jsonl_with_line_number(tmp_path):
    module = _load_assembler()
    source = tmp_path / "bad.jsonl"
    source.write_text('{"session_id":"ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        module.load_jsonl(source)
