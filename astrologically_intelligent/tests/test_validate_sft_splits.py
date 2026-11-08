import json
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_sft_splits.py"
SPEC = importlib.util.spec_from_file_location("validate_sft_splits", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _write(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _row(family, user, answer="ok"):
    return {"source_family_id": family, "messages": [
        {"role": "user", "content": user},
        {"role": "assistant", "content": answer},
    ]}


def test_disjoint_splits_pass(tmp_path):
    paths = {
        "train": _write(tmp_path / "train.jsonl", [_row("a", "one"), _row("b", "two")]),
        "validation": _write(tmp_path / "validation.jsonl", [_row("c", "three")]),
        "test": _write(tmp_path / "test.jsonl", [_row("d", "four")]),
    }
    report = MODULE.validate_splits(paths)
    assert report["status"] == "valid"
    assert report["splits"]["train"]["examples"] == 2


def test_family_leakage_fails_even_when_conversations_differ(tmp_path):
    paths = {
        "train": _write(tmp_path / "train.jsonl", [_row("same-family", "one")]),
        "validation": _write(tmp_path / "validation.jsonl", [_row("same-family", "two")]),
        "test": _write(tmp_path / "test.jsonl", [_row("held-out", "three")]),
    }
    try:
        MODULE.validate_splits(paths)
    except ValueError as exc:
        assert "family leakage" in str(exc)
    else:
        raise AssertionError("family leakage was accepted")


def test_normalized_duplicate_content_fails_without_family_ids(tmp_path):
    same = {"messages": [
        {"role": "user", "content": "same   prompt"},
        {"role": "assistant", "content": "same answer"},
    ]}
    paths = {
        "train": _write(tmp_path / "train.jsonl", [same]),
        "validation": _write(tmp_path / "validation.jsonl", [same]),
        "test": _write(tmp_path / "test.jsonl", [_row("other", "unique")]),
    }
    try:
        MODULE.validate_splits(paths)
    except ValueError as exc:
        assert "conversation leakage" in str(exc)
    else:
        raise AssertionError("duplicate content was accepted")


def test_malformed_example_fails_closed(tmp_path):
    paths = {
        "train": _write(tmp_path / "train.jsonl", [{"messages": []}]),
        "validation": _write(tmp_path / "validation.jsonl", [_row("b", "two")]),
        "test": _write(tmp_path / "test.jsonl", [_row("c", "three")]),
    }
    try:
        MODULE.validate_splits(paths)
    except ValueError as exc:
        assert "non-empty array" in str(exc)
    else:
        raise AssertionError("empty messages were accepted")


def test_seed_family_id_in_repository_metadata_is_detected(tmp_path):
    row = {"metadata": {"seed_family_id": "family-meta"}, "messages": [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "answer"},
    ]}
    assert MODULE._family_id(row) == "family-meta"


def test_assistant_tool_call_without_text_is_valid_and_included_in_digest(tmp_path):
    row = {
        "source_family_id": "tool-family",
        "messages": [
            {"role": "user", "content": "Create a reminder."},
            {"role": "assistant", "content": "", "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "manage_tasks", "arguments": json.dumps({"action": "create"})},
            }]},
            {"role": "tool", "tool_call_id": "call-1", "content": "Created."},
            {"role": "assistant", "content": "The reminder was created."},
        ],
    }
    normalized = MODULE._conversation(row, 1)
    assert normalized[1]["tool_calls"][0]["name"] == "manage_tasks"
    assert normalized[1]["tool_calls"][0]["arguments"] == {"action": "create"}


def test_malformed_tool_call_arguments_fail_closed(tmp_path):
    row = {
        "messages": [
            {"role": "user", "content": "Do something."},
            {"role": "assistant", "content": "", "tool_calls": [{
                "id": "call-1",
                "function": {"name": "manage_tasks", "arguments": json.dumps({"action": "create"})},
            }]},
        ],
    }
    try:
        MODULE._conversation(row, 1)
    except ValueError as exc:
        assert "invalid JSON arguments" in str(exc)
    else:
        raise AssertionError("malformed tool arguments were accepted")
