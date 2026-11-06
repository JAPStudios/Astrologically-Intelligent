import numpy as np
import pytest

from src.neural_network import NeuralNetworkClassifier


def _dataset():
    rng = np.random.default_rng(12)
    centers = np.array([[-2.0, -1.5], [2.0, -1.5], [0.0, 2.0]])
    labels = np.repeat(np.arange(3), 80)
    features = np.vstack([rng.normal(center, 0.45, (80, 2)) for center in centers])
    return features, labels


def test_network_learns_three_separable_classes():
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, 16, 3, learning_rate=0.02, seed=7)
    before = model.evaluate(features, labels)
    history = model.fit(features, labels, epochs=100, batch_size=24)
    after = model.evaluate(features, labels)
    assert after["loss"] < before["loss"] * 0.2
    assert after["accuracy"] > 0.98
    assert len(history) == 100
    assert np.allclose(model.predict_proba(features).sum(axis=1), 1.0)


def test_checkpoint_round_trip_preserves_predictions_and_optimizer(tmp_path):
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, 12, 3, seed=3)
    model.fit(features, labels, epochs=4)
    expected = model.predict_proba(features[:8])
    checkpoint = tmp_path / "learned-network.npz"
    model.save(checkpoint)
    restored = NeuralNetworkClassifier.load(checkpoint)
    assert np.allclose(restored.predict_proba(features[:8]), expected)
    assert restored._step == model._step
    assert np.array_equal(restored.predict(features[:8]), labels[:8])


def test_checkpoint_rejects_negative_adam_second_moment(tmp_path):
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, 8, 3, seed=37)
    model.fit(features, labels, epochs=2)
    checkpoint = tmp_path / "invalid-optimizer.npz"
    model.save(checkpoint)

    with np.load(checkpoint, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["adam_weights1_v"][0, 0] = -1.0
    np.savez_compressed(checkpoint, **arrays)

    with pytest.raises(ValueError, match="invalid optimizer state"):
        NeuralNetworkClassifier.load(checkpoint)


def test_checkpoint_rejects_invalid_architecture_metadata(tmp_path):
    model = NeuralNetworkClassifier(2, 8, 3, seed=43)
    checkpoint = tmp_path / "valid-metadata.npz"
    model.save(checkpoint)

    with np.load(checkpoint, allow_pickle=False) as archive:
        original = {name: archive[name].copy() for name in archive.files}

    invalid_metadata = {
        "fractional-dimensions": ("dimensions", np.array([2.5, 8, 3])),
        "zero-dimension": ("dimensions", np.array([2, 0, 3])),
        "fractional-layer-count": ("layer_count", np.array(1.5)),
        "non-finite-learning-rate": ("learning_rate", np.array(float("nan"))),
    }
    for name, (field, value) in invalid_metadata.items():
        arrays = {key: item.copy() for key, item in original.items()}
        arrays[field] = value
        invalid_checkpoint = tmp_path / f"{name}.npz"
        np.savez_compressed(invalid_checkpoint, **arrays)
        with pytest.raises(ValueError):
            NeuralNetworkClassifier.load(invalid_checkpoint)


def test_checkpoint_rejects_invalid_version_step_and_random_state(tmp_path):
    model = NeuralNetworkClassifier(2, 8, 3, seed=47)
    checkpoint = tmp_path / "valid-state.npz"
    model.save(checkpoint)

    with np.load(checkpoint, allow_pickle=False) as archive:
        original = {name: item.copy() for name, item in archive.items()}

    invalid_metadata = {
        "fractional-version": ("format_version", np.array(3.5)),
        "fractional-step": ("step", np.array(0.5)),
        "invalid-random-state": ("rng_state", np.array("{not-json")),
    }
    for name, (field, value) in invalid_metadata.items():
        arrays = {key: item.copy() for key, item in original.items()}
        arrays[field] = value
        invalid_checkpoint = tmp_path / f"{name}.npz"
        np.savez_compressed(invalid_checkpoint, **arrays)
        with pytest.raises(ValueError):
            NeuralNetworkClassifier.load(invalid_checkpoint)


def test_rejects_invalid_dimensions_and_training_data():
    with pytest.raises(ValueError, match="dimensions"):
        NeuralNetworkClassifier(2, 0, 3)
    model = NeuralNetworkClassifier(2, 4, 3)
    with pytest.raises(ValueError, match="columns"):
        model.predict([[1.0]])
    with pytest.raises(ValueError, match="class"):
        model.fit([[0.0, 1.0]], [3], epochs=1)


def test_rejects_non_finite_input():
    model = NeuralNetworkClassifier(2, 4, 2)
    with pytest.raises(ValueError, match="finite"):
        model.predict([[float("nan"), 0.0]])

def test_seed_reproduces_initialization_and_training_shuffle():
    features, labels = _dataset()
    first = NeuralNetworkClassifier(2, 10, 3, learning_rate=0.01, seed=41)
    second = NeuralNetworkClassifier(2, 10, 3, learning_rate=0.01, seed=41)

    first.fit(features, labels, epochs=8, batch_size=19)
    second.fit(features, labels, epochs=8, batch_size=19)

    assert np.array_equal(first.weights1, second.weights1)
    assert np.array_equal(first.weights2, second.weights2)
    assert np.array_equal(first.predict(features), second.predict(features))


def test_checkpoint_restores_training_random_state(tmp_path):
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, 10, 3, learning_rate=0.01, seed=17)
    model.fit(features, labels, epochs=3, batch_size=21)
    checkpoint = tmp_path / "resume-network.npz"
    model.save(checkpoint)

    restored = NeuralNetworkClassifier.load(checkpoint)
    model.fit(features, labels, epochs=5, batch_size=21)
    restored.fit(features, labels, epochs=5, batch_size=21)

    assert np.array_equal(model.weights1, restored.weights1)
    assert np.array_equal(model.bias1, restored.bias1)
    assert np.array_equal(model.weights2, restored.weights2)
    assert np.array_equal(model.bias2, restored.bias2)

def test_multilayer_network_learns_xor():
    base = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    features = np.repeat(base, 64, axis=0)
    labels = np.repeat(np.array([0, 1, 1, 0]), 64)
    model = NeuralNetworkClassifier(2, (16, 8), 2, learning_rate=0.02, seed=23)
    model.fit(features, labels, epochs=350, batch_size=16)
    assert model.evaluate(features, labels)["accuracy"] > 0.98
    assert np.allclose(model.predict_proba(features).sum(axis=1), 1.0)


def test_multilayer_checkpoint_round_trip_and_resume(tmp_path):
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, (12, 7), 3, learning_rate=0.01, seed=29)
    model.fit(features, labels, epochs=3, batch_size=20)
    checkpoint = tmp_path / "deep-network.npz"
    model.save(checkpoint)
    restored = NeuralNetworkClassifier.load(checkpoint)
    assert restored.hidden_sizes == (12, 7)
    assert np.array_equal(model.predict(features[:12]), restored.predict(features[:12]))
    model.fit(features, labels, epochs=4, batch_size=20)
    restored.fit(features, labels, epochs=4, batch_size=20)
    for name, parameter in model._parameters().items():
        assert np.array_equal(parameter, restored._parameters()[name])


def test_rejects_invalid_hidden_layer_sequence():
    with pytest.raises(ValueError, match="dimensions"):
        NeuralNetworkClassifier(2, (), 3)
    with pytest.raises(ValueError, match="dimensions"):
        NeuralNetworkClassifier(2, (8, 0, 4), 3)

def test_multilayer_backprop_matches_finite_difference():
    model = NeuralNetworkClassifier(2, (3, 2), 2, seed=31)
    features = np.array([[0.3, -0.7], [-0.2, 0.8]], dtype=float)
    labels = np.array([0, 1], dtype=int)
    activations, pre_activations, probabilities = model._forward(features)
    count = len(labels)
    delta = probabilities.copy()
    delta[np.arange(count), labels] -= 1.0
    delta /= count
    last = len(model._weights) - 1
    gradients = {f"weights{last + 1}": activations[-1].T @ delta,
                 f"bias{last + 1}": np.sum(delta, axis=0)}
    upstream = delta @ model._weights[last].T
    for layer in range(last - 1, -1, -1):
        upstream *= (pre_activations[layer] > 0.0)
        gradients[f"weights{layer + 1}"] = activations[layer].T @ upstream
        gradients[f"bias{layer + 1}"] = np.sum(upstream, axis=0)
        if layer:
            upstream = upstream @ model._weights[layer].T

    def loss():
        return model.evaluate(features, labels)["loss"]

    epsilon = 1e-6
    for name, parameter in model._parameters().items():
        index = tuple(0 for _ in parameter.shape)
        original = parameter[index]
        parameter[index] = original + epsilon
        upper = loss()
        parameter[index] = original - epsilon
        lower = loss()
        parameter[index] = original
        numerical = (upper - lower) / (2.0 * epsilon)
        assert numerical == pytest.approx(gradients[name][index], abs=2e-5)

def test_validation_monitoring_stops_early_and_restores_best_training_state():
    features, labels = _dataset()
    reference = NeuralNetworkClassifier(2, (12, 7), 3, learning_rate=0.01, seed=53)
    reference.fit(features, labels, epochs=1, batch_size=24)

    model = NeuralNetworkClassifier(2, (12, 7), 3, learning_rate=0.01, seed=53)
    history = model.fit(
        features,
        labels,
        epochs=20,
        batch_size=24,
        validation_data=(features, labels),
        patience=2,
        min_delta=1e6,
        restore_best_weights=True,
    )

    assert len(history) == 3
    assert {"validation_loss", "validation_accuracy"} <= history[0].keys()
    for name, parameter in reference._parameters().items():
        assert np.array_equal(parameter, model._parameters()[name])
    assert reference._step == model._step


def test_validation_options_require_valid_validation_data():
    features, labels = _dataset()
    model = NeuralNetworkClassifier(2, 8, 3, seed=59)
    with pytest.raises(ValueError, match="requires validation_data"):
        model.fit(features, labels, epochs=2, patience=1)
    with pytest.raises(ValueError, match="requires validation_data"):
        model.fit(features, labels, epochs=2, restore_best_weights=True)
    with pytest.raises(ValueError, match="validation_data"):
        model.fit(features, labels, epochs=2, validation_data=(features,))
    with pytest.raises(ValueError, match="patience"):
        model.fit(features, labels, epochs=2, validation_data=(features, labels), patience=0)

