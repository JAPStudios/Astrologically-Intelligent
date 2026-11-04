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
