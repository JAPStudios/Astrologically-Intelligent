"""Train a local character-level recurrent language model from UTF-8 text."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.character_language_model import CharacterLanguageModel


def _read_text(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 corpus {path}: {exc}") from exc
    if not value:
        raise ValueError(f"corpus is empty: {path}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, help="UTF-8 training text")
    parser.add_argument("checkpoint", type=Path, help="output .npz checkpoint path")
    parser.add_argument("--validation-file", type=Path, help="optional separate UTF-8 evaluation text")
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--steps-per-epoch", type=int, default=100)
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--prompt", default="", help="optional prompt for a generated sample")
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        training_text = _read_text(args.corpus)
        validation_text = _read_text(args.validation_file) if args.validation_file else None
        if args.validation_file:
            if args.corpus.resolve() == args.validation_file.resolve():
                raise ValueError("training and validation files must be separate")
            if training_text == validation_text:
                raise ValueError("training and validation text must not be identical")
        vocabulary = tuple(sorted(set(training_text)))
        model = CharacterLanguageModel(
            vocabulary,
            hidden_size=args.hidden_size,
            learning_rate=args.learning_rate,
            seed=args.seed,
        )
        history = model.fit(
            training_text,
            epochs=args.epochs,
            steps_per_epoch=args.steps_per_epoch,
            sequence_length=args.sequence_length,
            batch_size=args.batch_size,
            max_grad_norm=args.max_grad_norm,
        )
        validation_loss = (
            model.evaluate(validation_text, sequence_length=args.sequence_length,
                           batch_size=args.batch_size)
            if validation_text is not None else None
        )
        model.save(args.checkpoint)
        sample = (
            model.generate(args.prompt, max_new_tokens=args.max_new_tokens,
                           temperature=args.temperature, top_k=min(args.top_k, len(vocabulary)),
                           seed=args.seed)
            if args.prompt else None
        )
    except (OSError, ValueError, FloatingPointError) as exc:
        print(f"training failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "checkpoint": str(args.checkpoint),
        "vocabulary_size": len(vocabulary),
        "training_characters": len(training_text),
        "epochs_completed": len(history),
        "final_training_loss": history[-1]["loss"],
        "validation_loss": validation_loss,
        "sample": sample,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
