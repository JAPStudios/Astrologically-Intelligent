import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_hf_lora.py"
SPEC = importlib.util.spec_from_file_location("merge_hf_lora", SCRIPT)
assert SPEC and SPEC.loader
MERGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MERGER)


class Parameterized:
    weight = object()


class Container:
    weight = None


def test_qwen35_targets_are_expanded_only_inside_language_tower():
    modules = [
        ("model.language_model.layers.0.self_attn.q_proj", Parameterized()),
        ("model.language_model.layers.0.self_attn.k_proj", Parameterized()),
        ("model.visual.layers.0.attn.q_proj", Parameterized()),
        ("model.language_model.layers.0.self_attn", Container()),
    ]

    result = MERGER.language_target_modules(
        modules, ["q_proj", "k_proj"]
    )

    assert result == [
        "model.language_model.layers.0.self_attn.k_proj",
        "model.language_model.layers.0.self_attn.q_proj",
    ]


@pytest.mark.parametrize("targets", ["all-linear", ".*proj", [], None])
def test_rejects_broad_or_invalid_target_specs(targets):
    with pytest.raises(ValueError):
        MERGER.language_target_modules([], targets)


def test_rejects_visual_target_names():
    with pytest.raises(ValueError, match="visual/vision"):
        MERGER.language_target_modules(
            [("model.language_model.layers.0.q_proj", Parameterized())],
            ["visual.q_proj"],
        )


def test_rejects_target_list_with_no_language_tower_match():
    with pytest.raises(ValueError, match="no configured LoRA targets"):
        MERGER.language_target_modules(
            [("model.visual.layers.0.q_proj", Parameterized())],
            ["q_proj"],
        )


def test_qwen35_adapter_key_mapping_targets_language_tower():
    assert MERGER.QWEN35_KEY_MAPPING == {
        "model.layers.": "model.language_model.layers."
    }


@pytest.mark.parametrize(
    ("base", "adapter", "output"),
    [
        ("base", "adapter", "base"),
        ("base", "adapter", "adapter"),
        ("base", "adapter", "base/merged"),
        ("base", "adapter", "adapter/merged"),
        ("base", "adapter", "."),
    ],
)
def test_refuses_output_paths_overlapping_inputs(tmp_path, base, adapter, output):
    base_path = tmp_path / base
    adapter_path = tmp_path / adapter
    base_path.mkdir(parents=True, exist_ok=True)
    adapter_path.mkdir(parents=True, exist_ok=True)
    output_path = tmp_path / output

    with pytest.raises(ValueError, match="separate"):
        MERGER.validate_paths(base_path, adapter_path, output_path)


def test_accepts_separate_absent_output_path(tmp_path):
    base = tmp_path / "base"
    adapter = tmp_path / "adapter"
    output = tmp_path / "merged"
    base.mkdir()
    adapter.mkdir()

    MERGER.validate_paths(base, adapter, output)


def test_rejects_existing_file_as_output_path(tmp_path):
    base = tmp_path / "base"
    adapter = tmp_path / "adapter"
    output = tmp_path / "merged.bin"
    base.mkdir()
    adapter.mkdir()
    output.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        MERGER.validate_paths(base, adapter, output)


def test_rejects_nonempty_output_directory(tmp_path):
    base = tmp_path / "base"
    adapter = tmp_path / "adapter"
    output = tmp_path / "merged"
    base.mkdir()
    adapter.mkdir()
    output.mkdir()
    (output / "existing.bin").write_bytes(b"keep")

    with pytest.raises(ValueError, match="absent or empty"):
        MERGER.validate_paths(base, adapter, output)
