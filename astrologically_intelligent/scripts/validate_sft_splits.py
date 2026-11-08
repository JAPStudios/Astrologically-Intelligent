#!/usr/bin/env python3
"""Validate supervised chat corpora before model training.

The validator deliberately does not repair, deduplicate, or split data. It
fails closed when train/validation/test overlap by stable family identifier or
by normalized conversation content, so evaluation cannot silently leak.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_ALLOWED_ROLES = {"system", "developer", "user", "assistant", "tool"}
_FAMILY_KEYS = ("source_family_id", "family_id", "session_family_id")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _family_id(row: dict[str, Any]) -> str | None:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    for key in ("seed_family_id", *_FAMILY_KEYS):
        value = row.get(key) or metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _conversation(row: dict[str, Any], line: int) -> list[dict[str, Any]]:
    messages = row.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError(f"line {line}: 'messages' must be a non-empty array")
    normalized = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"line {line}: message {index} must be an object")
        role = message.get("role")
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"line {line}: message {index} has unsupported role")
        if not isinstance(content, str):
            raise ValueError(f"line {line}: message {index} content must be text")
        if not content.strip() and not (role == "assistant" and isinstance(tool_calls, list) and tool_calls):
            raise ValueError(f"line {line}: message {index} has empty content without assistant tool calls")
        item = {"role": role, "content": re.sub(r"\\s+", " ", content).strip()}
        if tool_calls is not None:
            if role != "assistant" or not isinstance(tool_calls, list) or not tool_calls:
                raise ValueError(f"line {line}: message {index} has invalid tool_calls")
            normalized_calls = []
            for call_index, call in enumerate(tool_calls):
                if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                    raise ValueError(f"line {line}: message {index} tool call {call_index} is malformed")
                function = call["function"]
                if not isinstance(function.get("name"), str) or not function["name"].strip():
                    raise ValueError(f"line {line}: message {index} tool call {call_index} has no function name")
                arguments = function.get("arguments")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"line {line}: message {index} tool call {call_index} has invalid JSON arguments") from exc
                if not isinstance(arguments, dict):
                    raise ValueError(f"line {line}: message {index} tool call {call_index} arguments must be an object")
                normalized_calls.append({
                    "id": call.get("id"),
                    "name": function["name"],
                    "arguments": arguments,
                })
            item["tool_calls"] = normalized_calls
        if role == "tool":
            tool_call_id = message.get("tool_call_id")
            if not isinstance(tool_call_id, str) or not tool_call_id.strip():
                raise ValueError(f"line {line}: tool message {index} must identify its tool_call_id")
            item["tool_call_id"] = tool_call_id
        normalized.append(item)
    if not any(message["role"] == "assistant" for message in normalized):
        raise ValueError(f"line {line}: conversation has no assistant target")
    if not any(message["role"] == "user" for message in normalized):
        raise ValueError(f"line {line}: conversation has no user input")
    return normalized


def read_split(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            row["_normalized_messages"] = _conversation(row, line_number)
            row["_source_line"] = line_number
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: split is empty")
    return rows


def validate_splits(paths: dict[str, Path]) -> dict[str, Any]:
    loaded = {name: read_split(path) for name, path in paths.items()}
    family_owners: dict[str, str] = {}
    content_owners: dict[str, str] = {}
    summary: dict[str, Any] = {}
    for split, rows in loaded.items():
        families = set()
        for row in rows:
            family = _family_id(row)
            if family:
                previous = family_owners.get(family)
                if previous and previous != split:
                    raise ValueError(f"family leakage: {family!r} appears in {previous} and {split}")
                family_owners[family] = split
                families.add(family)
            digest = hashlib.sha256(_canonical(row["_normalized_messages"]).encode("utf-8")).hexdigest()
            previous = content_owners.get(digest)
            if previous and previous != split:
                raise ValueError(f"conversation leakage: identical normalized conversation appears in {previous} and {split}")
            content_owners[digest] = split
        summary[split] = {"examples": len(rows), "families_with_ids": len(families)}
    return {"status": "valid", "splits": summary, "cross_split_family_leakage": 0, "cross_split_exact_content_leakage": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-family-id", action="store_true",
                        help="reject any example without a stable family identifier")
    args = parser.parse_args(argv)
    try:
        report = validate_splits({"train": args.train, "validation": args.validation, "test": args.test})
        if args.require_family_id:
            missing = {name: sum(1 for row in read_split(path) if not _family_id(row))
                       for name, path in {"train": args.train, "validation": args.validation, "test": args.test}.items()}
            if any(missing.values()):
                raise ValueError(f"examples missing stable family identifiers: {missing}")
    except (OSError, UnicodeError, ValueError) as exc:
        report = {"status": "invalid", "error": str(exc)}
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
