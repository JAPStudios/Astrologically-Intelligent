"""Trainable NumPy multilayer perceptron for task-specific local learning."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
from typing import Iterable, Sequence
import numpy as np


class NeuralNetworkClassifier:
    """Configurable multilayer perceptron for multiclass classification."""

    FORMAT_VERSION = 3

    def __init__(self, input_size: int, hidden_size: int | Sequence[int], output_size: int,
                 *, learning_rate: float = 1e-3, seed: int | None = None) -> None:
        if isinstance(hidden_size, bool):
            raise ValueError("hidden dimensions must be positive integers")
        hidden_sizes = (hidden_size,) if isinstance(hidden_size, int) else tuple(hidden_size)
        dimensions = (input_size, *hidden_sizes, output_size)
        if (not hidden_sizes or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0
                                    for v in dimensions)):
            raise ValueError("network dimensions must be positive integers")
        if output_size < 2:
            raise ValueError("output_size must be at least 2 for classification")
        if (
            isinstance(learning_rate, (bool, np.bool_))
            or not isinstance(learning_rate, (int, float, np.integer, np.floating))
            or not np.isfinite(learning_rate)
            or learning_rate <= 0
        ):
            raise ValueError("learning_rate must be a positive finite number")
        self.input_size = input_size
        self.hidden_sizes = tuple(hidden_sizes)
        self.hidden_size = self.hidden_sizes[0]
        self.output_size = output_size
        self.learning_rate = float(learning_rate)
        self._rng = np.random.default_rng(seed)
        self._weights, self._biases = [], []
        for fan_in, fan_out in zip(dimensions[:-1], dimensions[1:]):
            self._weights.append(self._rng.normal(0.0, np.sqrt(2.0 / fan_in),
                                                  (fan_in, fan_out)))
            self._biases.append(np.zeros(fan_out, dtype=np.float64))
        self._step = 0
        self._adam = {name: (np.zeros_like(value), np.zeros_like(value))
                      for name, value in self._parameters().items()}

    @property
    def weights1(self):
        return self._weights[0]

    @property
    def bias1(self):
        return self._biases[0]

    @property
    def weights2(self):
        if len(self._weights) != 2:
            raise AttributeError("weights2 is only defined for one hidden layer")
        return self._weights[1]

    @property
    def bias2(self):
        if len(self._biases) != 2:
            raise AttributeError("bias2 is only defined for one hidden layer")
        return self._biases[1]

    def _parameters(self):
        result = {}
        for i, (weights, bias) in enumerate(zip(self._weights, self._biases), 1):
            result[f"weights{i}"], result[f"bias{i}"] = weights, bias
        return result

    def _forward(self, features):
        activations, pre_activations = [features], []
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            for weights, bias in zip(self._weights[:-1], self._biases[:-1]):
                linear = activations[-1] @ weights + bias
                if not np.isfinite(linear).all():
                    raise FloatingPointError("non-finite hidden-layer activation")
                pre_activations.append(linear)
                activations.append(np.maximum(linear, 0.0))
            logits = activations[-1] @ self._weights[-1] + self._biases[-1]
            if not np.isfinite(logits).all():
                raise FloatingPointError("non-finite output logits")
            exponentials = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            denominator = np.sum(exponentials, axis=1, keepdims=True)
            probabilities = exponentials / denominator
        if not np.isfinite(probabilities).all():
            raise FloatingPointError("non-finite output probabilities")
        return activations, pre_activations, probabilities

    def predict_proba(self, features: Iterable[Iterable[float]]) -> np.ndarray:
        return self._forward(self._features(features))[2]

    def predict(self, features: Iterable[Iterable[float]]) -> np.ndarray:
        return np.argmax(self.predict_proba(features), axis=1)

    def evaluate(self, features, labels, *, class_weights=None):
        values = self._features(features)
        targets = self._labels(labels, len(values))
        weights = self._class_weights(class_weights)
        sample_weights = weights[targets]
        probabilities = self._forward(values)[2]
        selected = np.clip(probabilities[np.arange(len(targets)), targets], 1e-12, 1.0)
        weighted_loss = -np.sum(sample_weights * np.log(selected)) / np.sum(sample_weights)
        return {"loss": float(weighted_loss),
                "accuracy": float(np.mean(np.argmax(probabilities, axis=1) == targets))}

    def _class_weights(self, class_weights):
        if class_weights is None:
            return np.ones(self.output_size, dtype=np.float64)
        try:
            raw = np.asarray(class_weights)
        except (TypeError, ValueError) as exc:
            raise ValueError("class_weights must contain one positive finite number per class") from exc
        if raw.dtype.kind not in "iuf" or raw.shape != (self.output_size,):
            raise ValueError("class_weights must contain one positive finite number per class")
        weights = raw.astype(np.float64, copy=False)
        if not np.isfinite(weights).all() or np.any(weights <= 0.0):
            raise ValueError("class_weights must contain one positive finite number per class")
        return weights

    def fit(self, features, labels, *, epochs: int = 100, batch_size: int = 32,
            shuffle: bool = True, validation_data=None, patience: int | None = None,
            min_delta: float = 0.0, restore_best_weights: bool = False,
            max_grad_norm: float | None = None,
            class_weights: Sequence[float] | None = None) -> list[dict[str, float]]:
        values = self._features(features)
        targets = self._labels(labels, len(values))
        if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1:
            raise ValueError("epochs must be a positive integer")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        if not isinstance(shuffle, bool):
            raise ValueError("shuffle must be a boolean")
        if patience is not None and (
            isinstance(patience, bool) or not isinstance(patience, int) or patience < 1
        ):
            raise ValueError("patience must be a positive integer")
        if (
            isinstance(min_delta, (bool, np.bool_))
            or not isinstance(min_delta, (int, float, np.integer, np.floating))
            or not np.isfinite(min_delta)
            or min_delta < 0
        ):
            raise ValueError("min_delta must be a non-negative finite number")
        if not isinstance(restore_best_weights, bool):
            raise ValueError("restore_best_weights must be a boolean")
        if max_grad_norm is not None and (
            isinstance(max_grad_norm, (bool, np.bool_))
            or not isinstance(max_grad_norm, (int, float, np.integer, np.floating))
            or not np.isfinite(max_grad_norm)
            or max_grad_norm <= 0
        ):
            raise ValueError("max_grad_norm must be a positive finite number or None")
        weights = self._class_weights(class_weights)
        validation = None
        if validation_data is not None:
            if not isinstance(validation_data, (tuple, list)) or len(validation_data) != 2:
                raise ValueError("validation_data must contain features and labels")
            validation_values = self._features(validation_data[0])
            validation_targets = self._labels(validation_data[1], len(validation_values))
            validation = (validation_values, validation_targets)
        if patience is not None and validation is None:
            raise ValueError("patience requires validation_data")
        if restore_best_weights and validation is None:
            raise ValueError("restore_best_weights requires validation_data")

        history = []
        best_loss = float("inf")
        best_state = None
        stale_epochs = 0
        for epoch in range(epochs):
            indices = self._rng.permutation(len(values)) if shuffle else np.arange(len(values))
            for start in range(0, len(indices), batch_size):
                chosen = indices[start:start + batch_size]
                x, y = values[chosen], targets[chosen]
                activations, pre_activations, probabilities = self._forward(x)
                count, last = len(chosen), len(self._weights) - 1
                delta = probabilities.copy()
                delta[np.arange(count), y] -= 1.0
                sample_weights = weights[y]
                delta *= sample_weights[:, None]
                delta /= np.sum(sample_weights)
                gradients = {f"weights{last + 1}": activations[-1].T @ delta,
                             f"bias{last + 1}": np.sum(delta, axis=0)}
                upstream = delta @ self._weights[last].T
                for layer in range(last - 1, -1, -1):
                    upstream *= (pre_activations[layer] > 0.0)
                    gradients[f"weights{layer + 1}"] = activations[layer].T @ upstream
                    gradients[f"bias{layer + 1}"] = np.sum(upstream, axis=0)
                    if layer:
                        upstream = upstream @ self._weights[layer].T
                if max_grad_norm is not None:
                    gradient_norm = float(np.sqrt(sum(
                        np.sum(np.square(gradient)) for gradient in gradients.values()
                    )))
                    if not np.isfinite(gradient_norm):
                        raise FloatingPointError("non-finite gradient norm")
                    if gradient_norm > max_grad_norm:
                        scale = float(max_grad_norm) / gradient_norm
                        gradients = {
                            name: gradient * scale
                            for name, gradient in gradients.items()
                        }
                self._adam_update(gradients)

            metrics = {"epoch": float(epoch + 1),
                       **self.evaluate(values, targets, class_weights=weights)}
            if validation is not None:
                validation_metrics = self.evaluate(*validation, class_weights=weights)
                metrics["validation_loss"] = validation_metrics["loss"]
                metrics["validation_accuracy"] = validation_metrics["accuracy"]
                if validation_metrics["loss"] < best_loss - min_delta:
                    best_loss = validation_metrics["loss"]
                    stale_epochs = 0
                    if restore_best_weights:
                        best_state = (
                            {name: value.copy() for name, value in self._parameters().items()},
                            {name: (moments[0].copy(), moments[1].copy())
                             for name, moments in self._adam.items()},
                            self._step,
                            copy.deepcopy(self._rng.bit_generator.state),
                        )
                else:
                    stale_epochs += 1
            history.append(metrics)
            if patience is not None and stale_epochs >= patience:
                break

        if best_state is not None:
            parameters, optimizer, step, rng_state = best_state
            for name, value in parameters.items():
                self._parameters()[name][...] = value
            self._adam = optimizer
            self._step = step
            self._rng.bit_generator.state = rng_state
        return history

    def _adam_update(self, gradients):
        parameters = self._parameters()
        if set(gradients) != set(parameters):
            raise ValueError("gradients must contain every network parameter exactly once")
        for name, gradient in gradients.items():
            if gradient.shape != parameters[name].shape or not np.isfinite(gradient).all():
                raise FloatingPointError(f"invalid gradient for {name}")
        next_step = self._step + 1
        b1, b2, epsilon = 0.9, 0.999, 1e-8
        updates = {}
        next_moments = {}
        for name, gradient in gradients.items():
            first, second = self._adam[name]
            next_first = b1 * first + (1.0 - b1) * gradient
            next_second = b2 * second + (1.0 - b2) * np.square(gradient)
            mhat = next_first / (1.0 - b1 ** next_step)
            vhat = next_second / (1.0 - b2 ** next_step)
            update = self.learning_rate * mhat / (np.sqrt(vhat) + epsilon)
            candidate = parameters[name] - update
            if not (np.isfinite(next_first).all() and np.isfinite(next_second).all()
                    and np.isfinite(candidate).all()):
                raise FloatingPointError(f"non-finite Adam update for {name}")
            updates[name] = candidate
            next_moments[name] = (next_first, next_second)
        for name, candidate in updates.items():
            parameters[name][...] = candidate
            self._adam[name] = next_moments[name]
        self._step = next_step

    def save(self, path: str | os.PathLike[str]) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp.npz")
        dimensions = [self.input_size, *self.hidden_sizes, self.output_size]
        arrays = {"format_version": np.array(self.FORMAT_VERSION),
                  "dimensions": np.array(dimensions), "learning_rate": np.array(self.learning_rate),
                  "step": np.array(self._step), "rng_state": np.array(json.dumps(self._rng.bit_generator.state)),
                  "layer_count": np.array(len(self._weights))}
        arrays.update({f"weights{i}": v for i, v in enumerate(self._weights, 1)})
        arrays.update({f"bias{i}": v for i, v in enumerate(self._biases, 1)})
        arrays.update({f"adam_{n}_m": s[0] for n, s in self._adam.items()})
        arrays.update({f"adam_{n}_v": s[1] for n, s in self._adam.items()})
        np.savez_compressed(temporary, **arrays)
        os.replace(temporary, destination)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "NeuralNetworkClassifier":
        with np.load(path, allow_pickle=False) as archive:
            raw_version = archive["format_version"]
            if raw_version.ndim != 0 or not np.issubdtype(raw_version.dtype, np.integer):
                raise ValueError("invalid neural-network checkpoint version")
            version = int(raw_version)
            if version not in (1, 2, cls.FORMAT_VERSION):
                raise ValueError(f"unsupported neural-network checkpoint version: {version}")
            raw_dimensions = archive["dimensions"]
            if (
                raw_dimensions.ndim != 1
                or not np.issubdtype(raw_dimensions.dtype, np.integer)
            ):
                raise ValueError("invalid checkpoint dimensions")
            dims = raw_dimensions.tolist()
            if len(dims) < 3 or any(dimension <= 0 for dimension in dims):
                raise ValueError("invalid checkpoint dimensions")
            learning_rate = archive["learning_rate"]
            if learning_rate.ndim != 0 or not np.isfinite(learning_rate):
                raise ValueError("invalid checkpoint learning rate")
            if float(learning_rate) <= 0:
                raise ValueError("invalid checkpoint learning rate")
            if version < 3:
                if len(dims) != 3:
                    raise ValueError("invalid legacy checkpoint dimensions")
                model = cls(dims[0], dims[1], dims[2],
                            learning_rate=float(learning_rate))
            else:
                layer_count = archive["layer_count"]
                if (
                    layer_count.ndim != 0
                    or not np.issubdtype(layer_count.dtype, np.integer)
                    or int(layer_count) != len(dims) - 1
                ):
                    raise ValueError("invalid checkpoint architecture")
                model = cls(dims[0], tuple(dims[1:-1]), dims[-1],
                            learning_rate=float(learning_rate))
            for name, parameter in model._parameters().items():
                value = archive[name]
                if value.shape != parameter.shape or not np.isfinite(value).all():
                    raise ValueError(f"invalid checkpoint parameter: {name}")
                parameter[...] = value
                first, second = archive[f"adam_{name}_m"].copy(), archive[f"adam_{name}_v"].copy()
                if (
                    any(v.shape != parameter.shape or not np.isfinite(v).all()
                        for v in (first, second))
                    or np.any(second < 0.0)
                ):
                    raise ValueError(f"invalid optimizer state: {name}")
                model._adam[name] = (first, second)
            raw_step = archive["step"]
            if raw_step.ndim != 0 or not np.issubdtype(raw_step.dtype, np.integer):
                raise ValueError("invalid optimizer step")
            model._step = int(raw_step)
            if model._step < 0:
                raise ValueError("invalid optimizer step")
            if version >= 2:
                try:
                    raw_rng_state = archive["rng_state"]
                    if raw_rng_state.ndim != 0 or raw_rng_state.dtype.kind not in {"U", "S"}:
                        raise ValueError
                    rng_state = json.loads(str(raw_rng_state))
                    if not isinstance(rng_state, dict):
                        raise ValueError
                    model._rng.bit_generator.state = rng_state
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError("invalid checkpoint random-generator state") from exc
            return model

    def _features(self, features):
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.input_size or not len(values):
            raise ValueError(f"features must be a non-empty 2D array with {self.input_size} columns")
        if not np.isfinite(values).all():
            raise ValueError("features must contain only finite numbers")
        return values

    def _labels(self, labels, count):
        values = np.asarray(labels)
        if values.ndim != 1 or len(values) != count or not np.issubdtype(values.dtype, np.integer):
            raise ValueError("labels must be a one-dimensional integer array matching the examples")
        if np.any(values < 0) or np.any(values >= self.output_size):
            raise ValueError("labels contain a class outside the configured output range")
        return values.astype(np.int64, copy=False)
