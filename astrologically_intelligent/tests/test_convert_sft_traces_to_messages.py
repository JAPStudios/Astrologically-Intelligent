import importlib.util
import json
from pathlib import Path

import pytest


APP_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = APP_ROOT / "scripts" / "convert_sft_traces_to_messages.py"
SPEC = importlib.util.spec_from_file_location("convert_sft_traces_to_messages", SCRIPT)
assert SPEC and SPEC.loader
CONVERTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONVERTER)


def valid_source(**overrides):
    row = {
        "session_id": "session-001",
        "user": "Explain the result.",
        "assistant": "The result is ready.",
        "tool_events": [],
        "metadata": {
            "seed_family_id": "family-001",
            "dataset_split": "train",
            "review_status": "approved",
        },
    }
    row.update(overrides)
    return row


def test_converts_text_only_trace_and_preserves_family_and_provenance():
    converted = CONVERTER.convert_row(valid_source(), 1)

    assert converted["messages"] == [
        {"role": "user", "content": "Explain the result."},
        {"role": "assistant", "content": "The result is ready."},
    ]
    assert converted["seed_family_id"] == "family-001"
    assert converted["metadata"]["seed_family_id"] == "family-001"
    assert converted["metadata"]["dataset_split"] == "train"
    assert converted["metadata"]["review_status"] == "approved"
    assert converted["metadata"]["source_trace_session_id"] == "session-001"
    assert converted["source_format"] == "approved_sft_trace_v1"


def test_rejects_tool_events_instead_of_fabricating_calls_or_results():
    row = valid_source(tool_events=[{"tool": "search", "output": "found"}])

    with pytest.raises(ValueError, match="verified call/result schema"):
        CONVERTER.convert_row(row, 1)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("user", "", "user must be non-empty text"),
        ("assistant", None, "assistant must be non-empty text"),
        ("session_id", "", "session_id must be a non-empty string"),
        ("tool_events", None, "tool_events must be an array"),
        ("metadata", [], "metadata must be an object"),
    ],
)
def test_rejects_incomplete_source_rows(field, value, message):
    with pytest.raises(ValueError, match=message):
        CONVERTER.convert_row(valid_source(**{field: value}), 3)


def test_rejects_missing_family_or_split():
    row = valid_source(metadata={"dataset_split": "train"})
    with pytest.raises(ValueError, match="stable seed_family_id"):
        CONVERTER.convert_row(row, 1)

    row = valid_source(metadata={"seed_family_id": "family-001"})
    with pytest.raises(ValueError, match="dataset_split"):
        CONVERTER.convert_row(row, 1)


def test_jsonl_conversion_writes_one_newline_terminated_record(tmp_path):
    source = tmp_path / "source.jsonl"
    output = tmp_path / "messages.jsonl"
    source.write_text(json.dumps(valid_source(), ensure_ascii=False) + "\n", encoding="utf-8")

    counts = CONVERTER.convert_file(source, output)

    assert counts == {"source_rows": 1, "converted_rows": 1}
    raw = output.read_bytes()
    assert raw.endswith(b"\n")
    converted = json.loads(raw)
    assert converted["messages"][0]["role"] == "user"


def test_failed_conversion_does_not_replace_existing_output(tmp_path):
    source = tmp_path / "source.jsonl"
    output = tmp_path / "messages.jsonl"
    output.write_text("previous\n", encoding="utf-8")
    source.write_text(json.dumps(valid_source(tool_events=[{"opaque": True}])) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="verified call/result schema"):
        CONVERTER.convert_file(source, output)

    assert output.read_text(encoding="utf-8") == "previous\n"
    assert not output.with_name(output.name + ".tmp").exists()

def test_expected_split_rejects_rows_from_another_partition():
    with pytest.raises(ValueError, match="expected validation split but source row is assigned to train"):
        CONVERTER.convert_row(valid_source(), 1, expected_split="validation")


def test_file_conversion_can_enforce_partition_identity(tmp_path):
    source = tmp_path / "train.jsonl"
    output = tmp_path / "validation.jsonl"
    source.write_text(json.dumps(valid_source()) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected validation split"):
        CONVERTER.convert_file(source, output, expected_split="validation")

    assert not output.exists()

def test_converted_partitions_pass_the_sft_data_gate(tmp_path):
    validator_path = APP_ROOT / "scripts" / "validate_sft_splits.py"
    validator_spec = importlib.util.spec_from_file_location("validate_sft_splits_for_conversion_test", validator_path)
    assert validator_spec and validator_spec.loader
    validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator)

    paths = {}
    for split in ("train", "validation", "test"):
        source = tmp_path / f"{split}-source.jsonl"
        output = tmp_path / f"{split}.jsonl"
        row = valid_source(
            session_id=f"session-{split}",
            metadata={"seed_family_id": f"family-{split}", "dataset_split": split},
        )
        source.write_text(json.dumps(row) + "\n", encoding="utf-8")
        CONVERTER.convert_file(source, output, expected_split=split)
        paths[split] = output

    report = validator.validate_splits(paths)

    assert report["status"] == "valid"
    assert report["cross_split_family_leakage"] == 0
    assert report["cross_split_exact_content_leakage"] == 0
