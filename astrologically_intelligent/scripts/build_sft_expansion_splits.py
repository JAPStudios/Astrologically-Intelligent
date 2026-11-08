#!/usr/bin/env python3
"""Build family-safe train/validation/test JSONL files from approved seeds and expansions."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]




def _safe_owner(value: object) -> str:
    owner = str(value or "").strip()
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", owner)
            or owner in {".", ".."}):
        raise ValueError(f"invalid SFT trace owner identifier: {owner!r}")
    return owner


def owner_trace_path(owner: object) -> Path:
    safe_owner = _safe_owner(owner)
    trace_dir = ROOT / "data" / "sft_traces"
    path = trace_dir / f"{safe_owner}.jsonl"
    if path.resolve().parent != trace_dir.resolve():
        raise ValueError(f"SFT trace path escapes its directory for owner {safe_owner!r}")
    return path


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-trace", type=Path, required=True)
    parser.add_argument("--review", type=Path, action="append", default=[])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_splits: dict[str, set[str]] = defaultdict(set)
    for seed in manifest["seeds"]:
        family = str(seed["seed_family_id"])
        split = str(seed["split"])
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid manifest split {split!r} for family {family}")
        manifest_splits[family].add(split)
    manifest_leaks = {
        family: values for family, values in manifest_splits.items() if len(values) > 1
    }
    if manifest_leaks:
        raise ValueError(f"manifest seed-family split leakage: {manifest_leaks}")
    split_by_family = {
        family: next(iter(values)) for family, values in manifest_splits.items()
    }
    retained_by_owner: dict[str, set[str]] = defaultdict(set)
    for review_path in args.review:
        report = json.loads(review_path.read_text(encoding="utf-8"))
        for item in report.get("results", []):
            if item.get("retained") is not True:
                continue
            owner = _safe_owner(item.get("owner"))
            session_id = str(item.get("session_id") or "").strip()
            if not owner or not session_id:
                raise ValueError("retained expansion review rows require an owner and session_id")
            retained_by_owner[owner].add(session_id)
    retained_sessions = {
        session_id for session_ids in retained_by_owner.values() for session_id in session_ids
    }

    corpus = rows(args.approved_trace)
    for owner, expected_sessions in sorted(retained_by_owner.items()):
        trace_path = owner_trace_path(owner)
        if not trace_path.is_file():
            raise FileNotFoundError(
                f"retained expansion trace is missing for owner {owner!r}: {trace_path}"
            )
        owner_rows = rows(trace_path)
        matching_rows = [
            row for row in owner_rows
            if str(row.get("session_id") or "") in expected_sessions
        ]
        found_sessions = {str(row.get("session_id") or "") for row in matching_rows}
        missing_sessions = expected_sessions - found_sessions
        if missing_sessions:
            raise ValueError(
                f"retained expansion sessions missing from owner trace {owner!r}: "
                f"{sorted(missing_sessions)}"
            )
        corpus.extend(matching_rows)

    seen_messages: dict[str, str] = {}
    cross_split_duplicates: dict[str, set[str]] = defaultdict(set)
    split_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    family_splits: dict[str, set[str]] = defaultdict(set)
    for row in corpus:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        family = str(
            metadata.get("seed_family_id")
            or row.get("seed_family_id")
            or f"seed:{row.get('session_id')}"
        )
        explicit_split = metadata.get("dataset_split") or row.get("dataset_split")
        if explicit_split:
            split = str(explicit_split)
        elif family in split_by_family:
            split = split_by_family[family]
        else:
            raise ValueError(
                f"no dataset split is recorded for seed family {family!r}; "
                "refusing to default an unassigned row to train"
            )
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split {split!r} for family {family}")
        # Track every source row before content deduplication. Otherwise an
        # exact duplicate assigned to another split can be skipped before its
        # family is checked, concealing train/validation/test leakage.
        family_splits[family].add(split)
        signature = json.dumps(
            [row.get("user"), row.get("assistant"), row.get("tool_events")],
            sort_keys=True,
            ensure_ascii=False,
        )
        if signature in seen_messages:
            if seen_messages[signature] != split:
                cross_split_duplicates[signature].update({seen_messages[signature], split})
            continue
        seen_messages[signature] = split
        split_rows[split].append(row)
    leaked = {family: values for family, values in family_splits.items() if len(values) > 1}
    if leaked:
        raise ValueError(f"seed-family split leakage: {leaked}")
    if cross_split_duplicates:
        split_leaks = sorted(
            (sorted(splits) for splits in cross_split_duplicates.values()),
            key=lambda splits: tuple(splits),
        )
        raise ValueError(f"duplicate SFT content crosses dataset splits: {split_leaks}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "validation", "test"):
        path = args.out_dir / f"{split}.jsonl"
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in split_rows[split])
            + ("\n" if split_rows[split] else ""),
            encoding="utf-8",
        )
    summary = {
        "turns": {split: len(split_rows[split]) for split in ("train", "validation", "test")},
        "sessions": len({str(row.get("session_id")) for row in corpus}),
        "families": len(family_splits),
        "retained_expansion_sessions": len(retained_sessions),
        "family_leaks": 0,
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["turns"], indent=2))


if __name__ == "__main__":
    main()
