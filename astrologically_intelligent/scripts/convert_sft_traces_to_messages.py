#!/usr/bin/env python3
"""Convert approved text-only SFT source traces to chat-message JSONL.

Tool-bearing traces are rejected until their event schema can be mapped to
faithful assistant tool calls and tool results. This converter never invents
tool arguments, call IDs, or tool outputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_ALLOWED_SPLITS = {"train", "validation", "test"}


def convert_row(
    row: Any, line_number: int, expected_split: str | None = None
) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"line {line_number}: source row must be an object")

    session_id = row.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError(f"line {line_number}: session_id must be a non-empty string")

    user = row.get("user")
    assistant = row.get("assistant")
    if not isinstance(user, str) or not user.strip():
        raise ValueError(f"line {line_number}: user must be non-empty text")
    if not isinstance(assistant, str) or not assistant.strip():
        raise ValueError(f"line {line_number}: assistant must be non-empty text")

    tool_events = row.get("tool_events")
    if not isinstance(tool_events, list):
        raise ValueError(f"line {line_number}: tool_events must be an array")
    if tool_events:
        raise ValueError(
            f"line {line_number}: tool-bearing traces are not convertible until "
            "tool_events have a verified call/result schema"
        )

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"line {line_number}: metadata must be an object")
    family_id = (
        metadata.get("seed_family_id")
        or row.get("seed_family_id")
        or metadata.get("source_family_id")
        or row.get("source_family_id")
    )
    if not isinstance(family_id, str) or not family_id.strip():
        raise ValueError(f"line {line_number}: stable seed_family_id is required")

    split = metadata.get("dataset_split") or row.get("dataset_split")
    if split not in _ALLOWED_SPLITS:
        raise ValueError(f"line {line_number}: dataset_split must be train, validation, or test")
    if expected_split is not None and split != expected_split:
        raise ValueError(
            f"line {line_number}: expected {expected_split} split but source row is assigned to {split}"
        )

    output_metadata = dict(metadata)
    output_metadata["seed_family_id"] = family_id.strip()
    output_metadata["dataset_split"] = split
    output_metadata["source_trace_session_id"] = session_id

    converted = {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "seed_family_id": family_id.strip(),
        "session_id": session_id,
        "metadata": output_metadata,
        "source_format": "approved_sft_trace_v1",
    }
    if isinstance(row.get("uuid"), str) and row["uuid"].strip():
        converted["source_uuid"] = row["uuid"]
    return converted


def convert_file(
    source: Path, destination: Path, expected_split: str | None = None
) -> dict[str, int]:
    counts = {"source_rows": 0, "converted_rows": 0}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        with source.open("r", encoding="utf-8") as reader, temporary.open(
            "w", encoding="utf-8", newline="\n"
        ) as writer:
            for line_number, raw in enumerate(reader, 1):
                if not raw.strip():
                    continue
                counts["source_rows"] += 1
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{source}:{line_number}: invalid JSON: {exc.msg}") from exc
                converted = convert_row(row, line_number, expected_split=expected_split)
                writer.write(json.dumps(converted, ensure_ascii=False) + "\n")
                counts["converted_rows"] += 1
        if counts["source_rows"] == 0:
            raise ValueError(f"{source}: source trace is empty")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-split", choices=sorted(_ALLOWED_SPLITS))
    args = parser.parse_args(argv)
    try:
        counts = convert_file(args.input, args.output, expected_split=args.expected_split)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(2, f"conversion refused: {exc}\n")
    print(json.dumps({"status": "converted", **counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
