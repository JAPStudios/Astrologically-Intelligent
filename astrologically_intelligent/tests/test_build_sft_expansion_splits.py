import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _run_builder(app_root: Path, manifest: Path, trace: Path, output: Path):
    return subprocess.run(
        [
            sys.executable,
            str(app_root / "scripts" / "build_sft_expansion_splits.py"),
            "--manifest",
            str(manifest),
            "--approved-trace",
            str(trace),
            "--out-dir",
            str(output),
        ],
        cwd=output.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_exact_duplicate_cannot_hide_seed_family_split_leakage(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    output = tmp_path / "splits"
    _write_json(
        manifest,
        {"seeds": [{"seed_family_id": "family-a", "split": "train"}]},
    )
    base = {
        "user": "Find the latest note",
        "assistant": "The latest note is available.",
        "tool_events": [{"tool": "manage_documents", "output": "success"}],
    }
    rows = [
        {
            **base,
            "session_id": "session-train",
            "metadata": {"seed_family_id": "family-a", "dataset_split": "train"},
        },
        {
            **base,
            "session_id": "session-validation",
            "metadata": {"seed_family_id": "family-a", "dataset_split": "validation"},
        },
    ]
    trace.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = _run_builder(app_root, manifest, trace, output)

    assert result.returncode != 0
    assert "seed-family split leakage" in result.stderr


def test_same_family_same_split_deduplicates_without_leakage(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    output = tmp_path / "splits"
    _write_json(
        manifest,
        {"seeds": [{"seed_family_id": "family-a", "split": "train"}]},
    )
    row = {
        "user": "Find the latest note",
        "assistant": "The latest note is available.",
        "tool_events": [{"tool": "manage_documents", "output": "success"}],
        "metadata": {"seed_family_id": "family-a", "dataset_split": "train"},
    }
    trace.write_text(
        "\n".join(json.dumps({**row, "session_id": f"session-{index}"}) for index in range(2)) + "\n",
        encoding="utf-8",
    )

    result = _run_builder(app_root, manifest, trace, output)

    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["turns"] == {"train": 1, "validation": 0, "test": 0}
    assert summary["family_leaks"] == 0
