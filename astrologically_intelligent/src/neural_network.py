"""A small, genuinely trainable neural classifier implemented with NumPy.

This module is intended for local learned components inside Astrologically
Intelligent. It performs dense-layer forward propagation, softmax inference,
cross-entropy backpropagation and Adam optimization. It does not call a remote
language model and does not pretend to be a pretrained language model.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np


class NeuralNetworkClassifier:
    """One-hidden-layer feed-forward neural network for multiclass learning."""

    FORMAT_VERSION = 2

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        output_size: int,
        *,
        learning_rate: float = 1e-3,
        seed: int | None = None,
    ) -> None:
        dimensions = (input_size, hidden_size, output_size)
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in dimensions):
            raise ValueError("network dimensions must be positive integers")
        if not np.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("learning_rate must be a positive finite number")
        self.input_size, self.hidden_size, self.output_size = dimensions
        self.learning_rate = float(learning_rate)
        self._rng = np.random.default_rng(seed)
        self.weights1 = self._rng.normal(0.0, np.sqrt(2.0 / input_size), (input_size, hidden_size))
        self.bias1 = np.zeros(hidden_size, dtype=np.float64)
        self.weights2 = self._rng.normal(0.0, np.sqrt(2.0 / hidden_size), (hidden_size, output_size))
        self.bias2 = np.zeros(output_size, dtype=np.float64)
        self._step = 0
        self._adam = {
            name: (np.zeros_like(value), np.zeros_like(value))
            for name, value in self._parameters().items()
        }

    def _parameters(self) -> dict[str, np.ndarray]:
        return {
            "weights1": self.weights1, "bias1": self.bias1,
            "weights2": self.weights2, "bias2": self.bias2,
        }

    def _forward(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        hidden_linear = features @ self.weights1 + self.bias1
        hidden = np.maximum(hidden_linear, 0.0)
        logits = hidden @ self.weights2 + self.bias2
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exponentials = np.exp(shifted)
        probabilities = exponentials / np.sum(exponentials, axis=1, keepdims=True)
        return hidden_linear, hidden, probabilities

    def predict_proba(self, features: Iterable[Iterable[float]]) -> np.ndarray:
        """Return one normalized class-probability row per input example."""
        values = self._features(features)
        return self._forward(values)[2]

    def predict(self, features: Iterable[Iterable[float]]) -> np.ndarray:
        """Return the most probable class index for each example."""
        return np.argmax(self.predict_proba(features), axis=1)

    def evaluate(self, features: Iterable[Iterable[float]], labels: Iterable[int]) -> dict[str, float]:
        """Return mean cross-entropy loss and classification accuracy."""
        values = self._features(features)
        targets = self._labels(labels, len(values))
        probabilities = self._forward(values)[2]
        selected = np.clip(probabilities[np.arange(len(targets)), targets], 1e-12, 1.0)
        return {
            "loss": float(-np.mean(np.log(selected))),
            "accuracy": float(np.mean(np.argmax(probabilities, axis=1) == targets)),
        }

    def fit(
        self,
        features: Iterable[Iterable[float]],
        labels: Iterable[int],
        *,
        epochs: int = 100,
        batch_size: int = 32,
        shuffle: bool = True,
    ) -> list[dict[str, float]]:
        """Train using mini-batch backpropagation and Adam; return epoch metrics."""
        values = self._features(features)
        targets = self._labels(labels, len(values))
        if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1:
            raise ValueError("epochs must be a positive integer")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        history: list[dict[str, float]] = []
        for _ in range(epochs):
            indices = self._rng.permutation(len(values)) if shuffle else np.arange(len(values))
            for start in range(0, len(indices), batch_size):
                batch_indices = indices[start:start + batch_size]
                batch_x = values[batch_indices]
                batch_y = targets[batch_indices]
                hidden_linear, hidden, probabilities = self._forward(batch_x)
                count = len(batch_indices)
                probabilities[np.arange(count), batch_y] -= 1.0
                probabilities /= count
                grad_w2 = hidden.T @ probabilities
                grad_b2 = np.sum(probabilities, axis=0)
                grad_hidden = probabilities @ self.weights2.T
                grad_hidden[hidden_linear <= 0.0] = 0.0
                grad_w1 = batch_x.T @ grad_hidden
                grad_b1 = np.sum(grad_hidden, axis=0)
                self._adam_update({
                    "weights1": grad_w1, "bias1": grad_b1,
                    "weights2": grad_w2, "bias2": grad_b2,
                })
            metrics = self.evaluate(values, targets)
            history.append({"epoch": float(len(history) + 1), **metrics})
        return history

    def _adam_update(self, gradients: dict[str, np.ndarray]) -> None:
        self._step += 1
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        parameters = self._parameters()
        for name, gradient in gradients.items():
            first, second = self._adam[name]
            first *= beta1
            first += (1.0 - beta1) * gradient
            second *= beta2
            second += (1.0 - beta2) * np.square(gradient)
            corrected_first = first / (1.0 - beta1 ** self._step)
            corrected_second = second / (1.0 - beta2 ** self._step)
            parameters[name] -= self.learning_rate * corrected_first / (np.sqrt(corrected_second) + epsilon)

    def save(self, path: str | os.PathLike[str]) -> None:
        """Persist architecture, optimizer state and parameters to a NumPy archive."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp.npz")
        np.savez_compressed(
            temporary,
            format_version=np.array(self.FORMAT_VERSION),
            dimensions=np.array([self.input_size, self.hidden_size, self.output_size]),
            learning_rate=np.array(self.learning_rate),
            step=np.array(self._step),
            rng_state=np.array(json.dumps(self._rng.bit_generator.state)),
            weights1=self.weights1, bias1=self.bias1,
            weights2=self.weights2, bias2=self.bias2,
            **{f"adam_{name}_m": state[0] for name, state in self._adam.items()},
            **{f"adam_{name}_v": state[1] for name, state in self._adam.items()},
        )
        os.replace(temporary, destination)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "NeuralNetworkClassifier":
        """Load a checkpoint without enabling pickle-based object deserialization."""
        with np.load(path, allow_pickle=False) as archive:
            version = int(archive["format_version"])
            if version not in (1, cls.FORMAT_VERSION):
                raise ValueError(f"unsupported neural-network checkpoint version: {version}")
            dimensions = archive["dimensions"].astype(int).tolist()
            model = cls(*dimensions, learning_rate=float(archive["learning_rate"]))
            for name, parameter in model._parameters().items():
                value = archive[name]
                if value.shape != parameter.shape or not np.isfinite(value).all():
                    raise ValueError(f"invalid checkpoint parameter: {name}")
                parameter[...] = value
                model._adam[name] = (
                    archive[f"adam_{name}_m"].copy(),
                    archive[f"adam_{name}_v"].copy(),
                )
                if any(state.shape != parameter.shape or not np.isfinite(state).all()
                       for state in model._adam[name]):
                    raise ValueError(f"invalid optimizer state: {name}")
            model._step = int(archive["step"])
            if version >= 2:
                model._rng.bit_generator.state = json.loads(str(archive["rng_state"]))
            if model._step < 0:
                raise ValueError("invalid optimizer step")
            return model

    def _features(self, features: Iterable[Iterable[float]]) -> np.ndarray:
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.input_size or values.shape[0] == 0:
            raise ValueError(f"features must be a non-empty 2D array with {self.input_size} columns")
        if not np.isfinite(values).all():
            raise ValueError("features must contain only finite numbers")
        return values

    def _labels(self, labels: Iterable[int], count: int) -> np.ndarray:
        values = np.asarray(labels)
        if values.ndim != 1 or len(values) != count or not np.issubdtype(values.dtype, np.integer):
            raise ValueError("labels must be a one-dimensional integer array matching the examples")
        if np.any(values < 0) or np.any(values >= self.output_size):
            raise ValueError("labels contain a class outside the configured output range")
        return values.astype(np.int64, copy=False)
