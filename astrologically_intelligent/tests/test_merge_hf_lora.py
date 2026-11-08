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
