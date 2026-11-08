import numpy as np
import pytest

from src.character_language_model import CharacterLanguageModel


def _model(seed=5):
    return CharacterLanguageModel(tuple("abc "), hidden_size=12, learning_rate=0.03, seed=seed)


def test_recurrent_language_model_learns_repeating_character_sequence():
    text = "abc " * 120
    model = _model()
    before = model.evaluate(text, sequence_length=8, batch_size=16)
    history = model.fit(text, epochs=8, steps_per_epoch=35, sequence_length=8, batch_size=16)
    after = model.evaluate(text, sequence_length=8, batch_size=16)
    assert after < before
    assert history[-1]["loss"] < history[0]["loss"]
    assert len(history) == 8
    generated = model.generate("a", max_new_tokens=24, temperature=0.7, top_k=1, seed=4)
    assert generated.startswith("a")
    assert set(generated) <= set("abc ")


def test_checkpoint_round_trip_and_resume_are_deterministic(tmp_path):
    text = "abc " * 80
    model = _model(seed=9)
    model.fit(text, epochs=2, steps_per_epoch=5, sequence_length=6, batch_size=4)
    checkpoint = tmp_path / "character-model.npz"
    model.save(checkpoint)
    restored = CharacterLanguageModel.load(checkpoint)
    assert restored.vocabulary == model.vocabulary
    assert restored._step == model._step
    assert model.generate("ab", max_new_tokens=20, seed=17) == restored.generate(
        "ab", max_new_tokens=20, seed=17
    )
    model.fit(text, epochs=1, steps_per_epoch=3, sequence_length=6, batch_size=4)
    restored.fit(text, epochs=1, steps_per_epoch=3, sequence_length=6, batch_size=4)
    for name, value in model._parameters.items():
        assert np.array_equal(value, restored._parameters[name])


def test_rejects_unknown_characters_and_invalid_generation_settings():
    model = _model()
    with pytest.raises(ValueError, match="outside the vocabulary"):
        model.fit("abcx abc", sequence_length=2)
    with pytest.raises(ValueError, match="temperature"):
        model.generate("a", temperature=0)
    with pytest.raises(ValueError, match="top_k"):
        model.generate("a", top_k=0)


def test_rejects_invalid_vocabulary_and_training_window():
    with pytest.raises(ValueError, match="unique"):
        CharacterLanguageModel(("a", "a"))
    with pytest.raises(ValueError, match="single-character"):
        CharacterLanguageModel(("ab", "c"))
    with pytest.raises(ValueError, match="longer than sequence_length"):
        _model().fit("abc", sequence_length=3)

def test_checkpoint_rejects_malformed_scalar_metadata(tmp_path):
    model = _model()
    checkpoint = tmp_path / "valid-character-model.npz"
    model.save(checkpoint)
    with np.load(checkpoint, allow_pickle=False) as archive:
        original = {name: archive[name].copy() for name in archive.files}

    invalid = {
        "fractional-version": ("format_version", np.array(1.5)),
        "fractional-hidden-size": ("hidden_size", np.array(12.5)),
        "non-finite-learning-rate": ("learning_rate", np.array(float("nan"))),
        "fractional-step": ("step", np.array(0.5)),
        "invalid-vocabulary-json": ("vocabulary", np.array("not-json")),
        "invalid-random-state": ("rng_state", np.array("{}")),
    }
    for name, (field, value) in invalid.items():
        arrays = {key: item.copy() for key, item in original.items()}
        arrays[field] = value
        invalid_checkpoint = tmp_path / f"{name}.npz"
        np.savez_compressed(invalid_checkpoint, **arrays)
        with pytest.raises(ValueError):
            CharacterLanguageModel.load(invalid_checkpoint)



def test_generation_rejects_non_finite_logits_instead_of_sampling_invalid_probabilities():
    model = _model()
    model._parameters["output_bias"][0] = 1e308
    with pytest.raises(FloatingPointError, match="non-finite logits"):
        model.generate("a", max_new_tokens=1, temperature=1e-308)


def test_generation_uses_validated_probability_path_for_every_generated_token(monkeypatch):
    model = _model()
    original = model._next_token_probabilities
    calls = []

    def tracked(hidden, *, temperature, top_k):
        calls.append((temperature, top_k))
        return original(hidden, temperature=temperature, top_k=top_k)

    monkeypatch.setattr(model, "_next_token_probabilities", tracked)
    generated = model.generate("ab", max_new_tokens=4, temperature=0.8, top_k=3, seed=12)

    assert generated.startswith("ab")
    assert len(generated) == 6
    assert calls == [(0.8, 3)] * 6


def test_evaluation_includes_partial_final_window_and_short_validation_text(monkeypatch):
    model = _model()
    original = model._forward
    observed = []

    def tracked(inputs):
        observed.append(inputs.copy())
        return original(inputs)

    monkeypatch.setattr(model, "_forward", tracked)
    short_loss = model.evaluate("abc", sequence_length=8, batch_size=4)
    assert np.isfinite(short_loss)
    assert len(observed) == 1
    assert observed[0].shape == (1, 2)

    observed.clear()
    loss = model.evaluate("abc abc", sequence_length=3, batch_size=2)
    assert np.isfinite(loss)
    assert [array.shape[1] for array in observed] == [3, 3]
    assert [int(value) for array in observed for value in array[0]] == [
        model._indices[char] for char in "abc ab"
    ]
