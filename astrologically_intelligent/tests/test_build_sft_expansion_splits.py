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

def test_manifest_rejects_one_seed_family_assigned_to_multiple_splits(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    output = tmp_path / "splits"
    _write_json(
        manifest,
        {
            "seeds": [
                {"seed_family_id": "family-a", "split": "train"},
                {"seed_family_id": "family-a", "split": "test"},
            ]
        },
    )
    trace.write_text("", encoding="utf-8")

    result = _run_builder(app_root, manifest, trace, output)

    assert result.returncode != 0
    assert "manifest seed-family split leakage" in result.stderr

def _load_split_builder():
    import importlib.util

    app_root = Path(__file__).resolve().parents[1]
    script = app_root / "scripts" / "build_sft_expansion_splits.py"
    spec = importlib.util.spec_from_file_location("build_sft_expansion_splits_under_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_split_builder_main(monkeypatch, module, manifest, trace, review, output):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_sft_expansion_splits.py",
            "--manifest",
            str(manifest),
            "--approved-trace",
            str(trace),
            "--review",
            str(review),
            "--out-dir",
            str(output),
        ],
    )
    module.main()


def test_retained_expansion_requires_owner_trace_file(tmp_path, monkeypatch):
    module = _load_split_builder()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    review = tmp_path / "review.json"
    output = tmp_path / "splits"
    _write_json(manifest, {"seeds": []})
    trace.write_text("", encoding="utf-8")
    _write_json(
        review,
        {"results": [{"owner": "owner-a", "session_id": "session-a", "retained": True}]},
    )

    import pytest

    with pytest.raises(FileNotFoundError, match="retained expansion trace is missing"):
        _run_split_builder_main(monkeypatch, module, manifest, trace, review, output)


def test_retained_expansion_requires_every_session_in_owner_trace(tmp_path, monkeypatch):
    module = _load_split_builder()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    review = tmp_path / "review.json"
    output = tmp_path / "splits"
    _write_json(manifest, {"seeds": []})
    trace.write_text("", encoding="utf-8")
    _write_json(
        review,
        {"results": [{"owner": "owner-a", "session_id": "session-a", "retained": True}]},
    )
    owner_trace = tmp_path / "data" / "sft_traces" / "owner-a.jsonl"
    owner_trace.parent.mkdir(parents=True)
    owner_trace.write_text(json.dumps({"session_id": "other-session"}) + "\n", encoding="utf-8")

    import pytest

    with pytest.raises(ValueError, match="retained expansion sessions missing"):
        _run_split_builder_main(monkeypatch, module, manifest, trace, review, output)


def test_retained_expansion_trace_is_included_in_declared_split(tmp_path, monkeypatch):
    module = _load_split_builder()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    review = tmp_path / "review.json"
    output = tmp_path / "splits"
    _write_json(manifest, {"seeds": []})
    trace.write_text("", encoding="utf-8")
    _write_json(
        review,
        {"results": [{"owner": "owner-a", "session_id": "session-a", "retained": True}]},
    )
    owner_trace = tmp_path / "data" / "sft_traces" / "owner-a.jsonl"
    owner_trace.parent.mkdir(parents=True)
    row = {
        "session_id": "session-a",
        "user": "Find a note",
        "assistant": "The note is ready.",
        "tool_events": [{"tool": "manage_documents"}],
        "metadata": {"seed_family_id": "family-a", "dataset_split": "test"},
    }
    owner_trace.write_text(json.dumps(row) + "\n", encoding="utf-8")

    _run_split_builder_main(monkeypatch, module, manifest, trace, review, output)

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["retained_expansion_sessions"] == 1
    assert summary["turns"] == {"train": 0, "validation": 0, "test": 1}

def test_unassigned_seed_family_is_not_silently_added_to_training(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    output = tmp_path / "splits"
    _write_json(manifest, {"seeds": []})
    trace.write_text(
        json.dumps({
            "session_id": "session-unassigned",
            "user": "Find a note",
            "assistant": "The note is ready.",
            "tool_events": [],
        }) + "\n",
        encoding="utf-8",
    )

    result = _run_builder(app_root, manifest, trace, output)

    assert result.returncode != 0
    assert "no dataset split is recorded" in result.stderr

def test_identical_content_cannot_cross_train_and_validation_splits(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    output = tmp_path / "splits"
    _write_json(
        manifest,
        {
            "seeds": [
                {"seed_family_id": "family-train", "split": "train"},
                {"seed_family_id": "family-validation", "split": "validation"},
            ]
        },
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
            "metadata": {"seed_family_id": "family-train", "dataset_split": "train"},
        },
        {
            **base,
            "session_id": "session-validation",
            "metadata": {"seed_family_id": "family-validation", "dataset_split": "validation"},
        },
    ]
    trace.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = _run_builder(app_root, manifest, trace, output)

    assert result.returncode != 0
    assert "duplicate SFT content crosses dataset splits" in result.stderr

def test_retained_expansion_owner_cannot_escape_trace_directory(tmp_path, monkeypatch):
    module = _load_split_builder()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    manifest = tmp_path / "manifest.json"
    trace = tmp_path / "approved.jsonl"
    review = tmp_path / "review.json"
    output = tmp_path / "splits"
    _write_json(manifest, {"seeds": []})
    trace.write_text("", encoding="utf-8")
    _write_json(
        review,
        {"results": [{"owner": "../../outside", "session_id": "session-a", "retained": True}]},
    )

    import pytest

    with pytest.raises(ValueError, match="invalid SFT trace owner identifier"):
        _run_split_builder_main(monkeypatch, module, manifest, trace, review, output)

