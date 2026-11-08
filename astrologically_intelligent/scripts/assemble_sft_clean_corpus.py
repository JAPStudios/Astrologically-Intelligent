#!/usr/bin/env python3
"""Assemble kept and validated repaired sessions into a clean SFT corpus."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL in {path} at line {line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL record in {path} at line {line_number} must be an object")
        records.append(row)
    return records


def _session_id(row: dict[str, Any], *, source: Path) -> str:
    value = str(row.get("session_id") or "").strip()
    if not value:
        raise ValueError(f"record in {source} is missing session_id")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--repairs", type=Path, action="append", default=[])
    parser.add_argument("--out-trace", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    input_paths = [args.trace, args.verdicts, *args.repairs]
    resolved_inputs = {path.resolve() for path in input_paths}
    resolved_outputs = {args.out_trace.resolve(), args.report.resolve()}
    if len(resolved_outputs) != 2 or resolved_inputs.intersection(resolved_outputs):
        raise ValueError("output paths must be distinct from each other and every input file")

    source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(args.trace):
        source[_session_id(row, source=args.trace)].append(row)

    verdicts: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(args.verdicts):
        session_id = _session_id(row, source=args.verdicts)
        if session_id in verdicts:
            raise ValueError(f"duplicate verdict for session {session_id!r}")
        if session_id not in source:
            raise ValueError(f"verdict references unknown source session {session_id!r}")
        verdicts[session_id] = row

    repaired: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in args.repairs:
        for row in load_jsonl(path):
            session_id = _session_id(row, source=path)
            if session_id not in source:
                raise ValueError(f"repair references unknown source session {session_id!r}")
            repaired[session_id].append(row)

    output: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for session_id in sorted(source):
        verdict = verdicts.get(session_id)
        decision = str((verdict or {}).get("verdict") or "missing")
        if decision not in {"keep", "repair", "exclude", "missing"}:
            raise ValueError(f"unsupported verdict {decision!r} for session {session_id!r}")
        if decision == "keep":
            output.extend(source[session_id])
            counts["kept"] += 1
        elif decision == "repair" and repaired.get(session_id):
            output.extend(repaired[session_id])
            counts["repaired"] += 1
        else:
            counts["excluded"] += 1
            excluded.append({
                "session_id": session_id,
                "verdict": decision,
                "issues": (verdict or {}).get("issues") or [],
                "repair_missing": decision == "repair" and session_id not in repaired,
            })

    args.out_trace.parent.mkdir(parents=True, exist_ok=True)
    args.out_trace.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in output) + ("\n" if output else ""),
        encoding="utf-8",
    )
    report = {
        "source_sessions": len(source),
        "output_sessions": counts["kept"] + counts["repaired"],
        "output_turns": len(output),
        "decisions": dict(counts),
        "excluded": excluded,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "excluded"}, indent=2))


if __name__ == "__main__":
    main()
