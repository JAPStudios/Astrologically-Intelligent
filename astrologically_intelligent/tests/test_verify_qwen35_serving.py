import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_qwen35_serving.py"
SPEC = importlib.util.spec_from_file_location("verify_qwen35_serving", SCRIPT)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def test_detects_material_served_model_logprob_difference():
    result = VERIFY.compare_logprobs(
        {"A": -0.1, "B": -0.2, "C": -0.3, "D": -0.4},
        {"A": -0.3, "B": -0.5, "C": -0.3, "D": -0.1},
        1e-4,
    )
    assert result["shared_candidates"] == 4
    assert result["changed_candidates"] == 3
    assert result["max_absolute_logprob_delta"] == pytest.approx(0.3)


def test_rejects_identical_served_models():
    values = {"A": -0.1, "B": -0.2, "C": -0.3}
    with pytest.raises(ValueError, match="appears identical"):
        VERIFY.compare_logprobs(values, dict(values), 1e-4)


def test_requires_multiple_shared_candidates():
    with pytest.raises(ValueError, match="shared top-token candidates"):
        VERIFY.compare_logprobs(
            {"A": -0.1, "B": -0.2, "C": -0.3},
            {"A": -0.4, "X": -0.2, "Y": -0.3},
            1e-4,
        )


def test_rejects_missing_logprobs():
    with pytest.raises(ValueError, match="did not return first-token"):
        VERIFY.parse_top_logprobs({"choices": [{"message": {"content": "x"}}]})
