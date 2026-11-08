"""Small trainable character-level recurrent language model implemented with NumPy.

This component learns next-character prediction from caller-supplied text. It is
an educational/local generative model, not a pretrained general-purpose LLM.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

import numpy as np


class CharacterLanguageModel:
    """A vanilla recurrent neural network trained with truncated BPTT and Adam."""

    FORMAT_VERSION = 1

    def __init__(
        self,
        vocabulary: Sequence[str],
        hidden_size: int = 64,
        *,
        learning_rate: float = 0.01,
        seed: int | None = None,
    ) -> None:
        tokens = tuple(vocabulary)
        if len(tokens) < 2 or any(not isinstance(token, str) or len(token) != 1 for token in tokens):
            raise ValueError("vocabulary must contain at least two single-character strings")
        if len(set(tokens)) != len(tokens):
            raise ValueError("vocabulary characters must be unique")
        if isinstance(hidden_size, bool) or not isinstance(hidden_size, int) or hidden_size < 1:
            raise ValueError("hidden_size must be a positive integer")
        if (isinstance(learning_rate, (bool, np.bool_))
                or not isinstance(learning_rate, (int, float, np.integer, np.floating))
                or not np.isfinite(learning_rate) or learning_rate <= 0):
            raise ValueError("learning_rate must be a positive finite number")

        self.vocabulary = tokens
        self._indices = {token: index for index, token in enumerate(tokens)}
        self.hidden_size = hidden_size
        self.learning_rate = float(learning_rate)
        self._rng = np.random.default_rng(seed)
        vocab_size = len(tokens)
        self._parameters = {
            "input_weights": self._rng.normal(0.0, 1.0 / np.sqrt(vocab_size), (vocab_size, hidden_size)),
            "recurrent_weights": self._rng.normal(0.0, 1.0 / np.sqrt(hidden_size), (hidden_size, hidden_size)),
            "hidden_bias": np.zeros(hidden_size, dtype=np.float64),
            "output_weights": self._rng.normal(0.0, 1.0 / np.sqrt(hidden_size), (hidden_size, vocab_size)),
            "output_bias": np.zeros(vocab_size, dtype=np.float64),
        }
        self._adam = {name: (np.zeros_like(value), np.zeros_like(value))
                      for name, value in self._parameters.items()}
        self._step = 0

    def _encode(self, text: str) -> np.ndarray:
        if not isinstance(text, str) or not text:
            raise ValueError("text must be a non-empty string")
        unknown = sorted(set(text).difference(self._indices))
        if unknown:
            raise ValueError(f"text contains characters outside the vocabulary: {unknown[:8]!r}")
        return np.fromiter((self._indices[char] for char in text), dtype=np.int64)

    def _forward(self, inputs: np.ndarray):
        batch_size, steps = inputs.shape
        hidden = np.zeros((batch_size, self.hidden_size), dtype=np.float64)
        states = [hidden]
        probabilities = []
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            for step in range(steps):
                hidden = np.tanh(
                    self._parameters["input_weights"][inputs[:, step]]
                    + hidden @ self._parameters["recurrent_weights"]
                    + self._parameters["hidden_bias"]
                )
                logits = hidden @ self._parameters["output_weights"] + self._parameters["output_bias"]
                logits -= np.max(logits, axis=1, keepdims=True)
                exponentials = np.exp(logits)
                probabilities.append(exponentials / np.sum(exponentials, axis=1, keepdims=True))
                states.append(hidden)
        result = np.stack(probabilities, axis=1)
        if not np.isfinite(result).all():
            raise FloatingPointError("language-model forward pass produced non-finite probabilities")
        return states, result

    def evaluate(self, text: str, *, sequence_length: int = 64, batch_size: int = 32) -> float:
        encoded = self._encode(text)
        self._validate_window(encoded, sequence_length, batch_size)
        starts = np.arange(0, len(encoded) - sequence_length, sequence_length)
        losses = []
        for offset in range(0, len(starts), batch_size):
            selected = starts[offset:offset + batch_size]
            x = np.stack([encoded[start:start + sequence_length] for start in selected])
            y = np.stack([encoded[start + 1:start + sequence_length + 1] for start in selected])
            _, probabilities = self._forward(x)
            chosen = np.clip(np.take_along_axis(probabilities, y[..., None], axis=2)[..., 0], 1e-12, 1.0)
            losses.extend((-np.log(chosen)).reshape(-1).tolist())
        if not losses:
            raise ValueError("text must contain at least two characters")
        return float(np.mean(losses))

    @staticmethod
    def _validate_window(encoded: np.ndarray, sequence_length: int, batch_size: int) -> None:
        if isinstance(sequence_length, bool) or not isinstance(sequence_length, int) or sequence_length < 1:
            raise ValueError("sequence_length must be a positive integer")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        if len(encoded) <= sequence_length:
            raise ValueError("training text must be longer than sequence_length")

    def fit(
        self,
        text: str,
        *,
        epochs: int = 10,
        steps_per_epoch: int = 100,
        sequence_length: int = 64,
        batch_size: int = 32,
        max_grad_norm: float = 1.0,
    ) -> list[dict[str, float]]:
        encoded = self._encode(text)
        self._validate_window(encoded, sequence_length, batch_size)
        for name, value in (("epochs", epochs), ("steps_per_epoch", steps_per_epoch)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (isinstance(max_grad_norm, (bool, np.bool_))
                or not isinstance(max_grad_norm, (int, float, np.integer, np.floating))
                or not np.isfinite(max_grad_norm) or max_grad_norm <= 0):
            raise ValueError("max_grad_norm must be a positive finite number")

        history = []
        max_start = len(encoded) - sequence_length - 1
        for epoch in range(epochs):
            epoch_losses = []
            for _ in range(steps_per_epoch):
                starts = self._rng.integers(0, max_start + 1, size=batch_size)
                inputs = np.stack([encoded[start:start + sequence_length] for start in starts])
                targets = np.stack([encoded[start + 1:start + sequence_length + 1] for start in starts])
                states, probabilities = self._forward(inputs)
                batch, steps = targets.shape
                delta = probabilities.copy()
                delta[np.arange(batch)[:, None], np.arange(steps)[None, :], targets] -= 1.0
                delta /= batch * steps
                gradients = {name: np.zeros_like(value) for name, value in self._parameters.items()}
                hidden_gradient = np.zeros((batch, self.hidden_size), dtype=np.float64)
                for step in range(steps - 1, -1, -1):
                    state = states[step + 1]
                    gradients["output_weights"] += state.T @ delta[:, step, :]
                    gradients["output_bias"] += np.sum(delta[:, step, :], axis=0)
                    hidden_gradient += delta[:, step, :] @ self._parameters["output_weights"].T
                    preactivation_gradient = hidden_gradient * (1.0 - np.square(state))
                    np.add.at(gradients["input_weights"], inputs[:, step], preactivation_gradient)
                    gradients["hidden_bias"] += np.sum(preactivation_gradient, axis=0)
                    gradients["recurrent_weights"] += states[step].T @ preactivation_gradient
                    hidden_gradient = preactivation_gradient @ self._parameters["recurrent_weights"].T
                norm = float(np.sqrt(sum(np.sum(np.square(grad)) for grad in gradients.values())))
                if not np.isfinite(norm):
                    raise FloatingPointError("language-model gradient norm is non-finite")
                if norm > max_grad_norm:
                    scale = float(max_grad_norm) / norm
                    gradients = {name: grad * scale for name, grad in gradients.items()}
                self._adam_update(gradients)
                chosen = np.clip(np.take_along_axis(probabilities, targets[..., None], axis=2)[..., 0], 1e-12, 1.0)
                epoch_losses.append(float(-np.mean(np.log(chosen))))
            history.append({"epoch": float(epoch + 1), "loss": float(np.mean(epoch_losses))})
        return history

    def _adam_update(self, gradients: dict[str, np.ndarray]) -> None:
        next_step = self._step + 1
        updates = {}
        moments = {}
        for name, parameter in self._parameters.items():
            gradient = gradients[name]
            if gradient.shape != parameter.shape or not np.isfinite(gradient).all():
                raise FloatingPointError(f"invalid language-model gradient: {name}")
            first, second = self._adam[name]
            first = 0.9 * first + 0.1 * gradient
            second = 0.999 * second + 0.001 * np.square(gradient)
            first_hat = first / (1.0 - 0.9 ** next_step)
            second_hat = second / (1.0 - 0.999 ** next_step)
            candidate = parameter - self.learning_rate * first_hat / (np.sqrt(second_hat) + 1e-8)
            if not (np.isfinite(first).all() and np.isfinite(second).all() and np.isfinite(candidate).all()):
                raise FloatingPointError(f"non-finite language-model update: {name}")
            updates[name] = candidate
            moments[name] = (first, second)
        for name, candidate in updates.items():
            self._parameters[name][...] = candidate
            self._adam[name] = moments[name]
        self._step = next_step

    def generate(
        self,
        prompt: str,
        *,
        max_new_tokens: int = 200,
        temperature: float = 1.0,
        top_k: int | None = None,
        seed: int | None = None,
    ) -> str:
        encoded = self._encode(prompt)
        if isinstance(max_new_tokens, bool) or not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            raise ValueError("max_new_tokens must be a non-negative integer")
        if (isinstance(temperature, (bool, np.bool_))
                or not isinstance(temperature, (int, float, np.integer, np.floating))
                or not np.isfinite(temperature) or temperature <= 0):
            raise ValueError("temperature must be a positive finite number")
        if top_k is not None and (isinstance(top_k, bool) or not isinstance(top_k, int)
                                  or not 1 <= top_k <= len(self.vocabulary)):
            raise ValueError("top_k must be between 1 and the vocabulary size")
        rng = np.random.default_rng(seed) if seed is not None else self._rng
        hidden = np.zeros(self.hidden_size, dtype=np.float64)
        probabilities = None
        for token in encoded:
            hidden = np.tanh(self._parameters["input_weights"][token]
                             + hidden @ self._parameters["recurrent_weights"]
                             + self._parameters["hidden_bias"])
            logits = hidden @ self._parameters["output_weights"] + self._parameters["output_bias"]
            logits = logits / float(temperature)
            if top_k is not None and top_k < len(logits):
                keep = np.argpartition(logits, -top_k)[-top_k:]
                filtered = np.full_like(logits, -np.inf)
                filtered[keep] = logits[keep]
                logits = filtered
            logits -= np.max(logits)
            probabilities = np.exp(logits)
            probabilities /= np.sum(probabilities)
        output = list(prompt)
        for _ in range(max_new_tokens):
            next_token = int(rng.choice(len(self.vocabulary), p=probabilities))
            output.append(self.vocabulary[next_token])
            hidden = np.tanh(self._parameters["input_weights"][next_token]
                             + hidden @ self._parameters["recurrent_weights"]
                             + self._parameters["hidden_bias"])
            logits = hidden @ self._parameters["output_weights"] + self._parameters["output_bias"]
            logits = logits / float(temperature)
            if top_k is not None and top_k < len(logits):
                keep = np.argpartition(logits, -top_k)[-top_k:]
                filtered = np.full_like(logits, -np.inf)
                filtered[keep] = logits[keep]
                logits = filtered
            logits -= np.max(logits)
            probabilities = np.exp(logits)
            probabilities /= np.sum(probabilities)
        return "".join(output)

    def save(self, path: str | os.PathLike[str]) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp.npz")
        arrays = {
            "format_version": np.array(self.FORMAT_VERSION),
            "vocabulary": np.array(json.dumps(self.vocabulary, ensure_ascii=False)),
            "hidden_size": np.array(self.hidden_size),
            "learning_rate": np.array(self.learning_rate),
            "step": np.array(self._step),
            "rng_state": np.array(json.dumps(self._rng.bit_generator.state)),
        }
        arrays.update(self._parameters)
        arrays.update({f"adam_{name}_m": value[0] for name, value in self._adam.items()})
        arrays.update({f"adam_{name}_v": value[1] for name, value in self._adam.items()})
        np.savez_compressed(temporary, **arrays)
        os.replace(temporary, destination)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "CharacterLanguageModel":
        with np.load(path, allow_pickle=False) as archive:
            version = archive["format_version"]
            if version.ndim != 0 or int(version) != cls.FORMAT_VERSION:
                raise ValueError("unsupported language-model checkpoint version")
            try:
                vocabulary = json.loads(str(archive["vocabulary"]))
                hidden_size = int(archive["hidden_size"])
                learning_rate = float(archive["learning_rate"])
                step = int(archive["step"])
                rng_state = json.loads(str(archive["rng_state"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError("invalid language-model checkpoint metadata") from exc
            if step < 0:
                raise ValueError("invalid language-model optimizer step")
            model = cls(vocabulary, hidden_size, learning_rate=learning_rate)
            if not isinstance(rng_state, dict):
                raise ValueError("invalid language-model random-generator state")
            try:
                model._rng.bit_generator.state = rng_state
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid language-model random-generator state") from exc
            for name, parameter in model._parameters.items():
                value = archive[name]
                first = archive[f"adam_{name}_m"]
                second = archive[f"adam_{name}_v"]
                if (value.shape != parameter.shape or first.shape != parameter.shape
                        or second.shape != parameter.shape or not np.isfinite(value).all()
                        or not np.isfinite(first).all() or not np.isfinite(second).all()
                        or np.any(second < 0.0)):
                    raise ValueError(f"invalid language-model checkpoint tensor: {name}")
                parameter[...] = value
                model._adam[name] = (first.copy(), second.copy())
            model._step = step
            return model
