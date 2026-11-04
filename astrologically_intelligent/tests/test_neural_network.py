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

