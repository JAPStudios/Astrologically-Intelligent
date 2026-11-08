#!/usr/bin/env python3
"""Merge a Qwen3.5 causal-LoRA adapter into the full multimodal checkpoint.

The adapter is loaded into the image/text model, with causal text-tower keys
remapped to the language tower. The merge is refused unless a deterministic
logit probe proves that the adapter changes model output.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable

QWEN35_KEY_MAPPING = {"model.layers.": "model.language_model.layers."}


def language_target_modules(
    named_modules: Iterable[tuple[str, object]], configured_targets: object
) -> list[str]:
    """Expand LoRA suffix targets to exact language-tower module names only."""
    if isinstance(configured_targets, str):
        raise ValueError(
            "adapter target_modules must be an explicit list; regex and all-linear "
            "targets are refused because they can include the visual tower"
        )
    if not isinstance(configured_targets, (list, set, tuple)) or not configured_targets:
        raise ValueError("adapter target_modules must be a non-empty list")
    suffixes = [str(item).strip() for item in configured_targets]
    if any(not item or "visual" in item.lower() or "vision" in item.lower() for item in suffixes):
        raise ValueError("visual/vision targets are not permitted in a text-only Qwen3.5 adapter")

    selected: list[str] = []
    for name, module in named_modules:
        if "language_model.layers." not in name:
            continue
        if not any(name == suffix or name.endswith("." + suffix) for suffix in suffixes):
            continue
        # LoRA projection targets must be parameterized modules, not containers.
        if hasattr(module, "weight") and getattr(module, "weight") is not None:
            selected.append(name)
    if not selected:
        raise ValueError("no configured LoRA targets matched the Qwen3.5 language tower")
    return sorted(set(selected))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Local full Qwen3.5-9B base checkpoint")
    parser.add_argument("--adapter", type=Path, required=True, help="PEFT adapter directory")
    parser.add_argument("--output", type=Path, required=True, help="New merged checkpoint directory")
    parser.add_argument("--verify-prompt", required=True, help="Deterministic text used for adapter activation verification")
    parser.add_argument("--min-logit-delta", type=float, default=1e-6)
    parser.add_argument("--dtype", choices=("bfloat16", "float16", "float32"), default="bfloat16")
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.base.is_dir():
        raise SystemExit(f"base checkpoint directory does not exist: {args.base}")
    if not (args.adapter / "adapter_config.json").is_file():
        raise SystemExit(f"adapter_config.json is missing: {args.adapter}")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"output directory must be absent or empty: {args.output}")
    if not math.isfinite(args.min_logit_delta) or args.min_logit_delta <= 0:
        raise SystemExit("--min-logit-delta must be a finite positive number")
    if not args.verify_prompt.strip():
        raise SystemExit("--verify-prompt must contain text")

    try:
        import torch
        from peft import PeftConfig, PeftModel
        from transformers import AutoConfig, AutoModelForImageTextToText, AutoProcessor
    except ImportError as exc:
        raise SystemExit(
            "merge dependencies are unavailable; install the model-training "
            "requirements before running this script"
        ) from exc

    dtype = {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }[args.dtype]

    base_config = AutoConfig.from_pretrained(
        str(args.base), trust_remote_code=args.trust_remote_code
    )
    if getattr(base_config, "model_type", None) != "qwen3_5":
        raise SystemExit(
            f"expected a Qwen3.5 checkpoint (model_type=qwen3_5), got "
            f"{getattr(base_config, 'model_type', None)!r}"
        )

    print("Loading full multimodal Qwen3.5 base checkpoint...", flush=True)
    model = AutoModelForImageTextToText.from_pretrained(
        str(args.base),
        dtype=dtype,
        device_map="auto",
        trust_remote_code=args.trust_remote_code,
    )
    processor = AutoProcessor.from_pretrained(
        str(args.base), trust_remote_code=args.trust_remote_code
    )

    config = PeftConfig.from_pretrained(str(args.adapter))
    if not hasattr(config, "target_modules"):
        raise SystemExit("adapter configuration has no explicit target_modules")
    targets = language_target_modules(model.named_modules(), config.target_modules)
    config.target_modules = set(targets)
    # Restrict the adapter to the text tower by replacing broad suffix matches
    # with the exact language-tower module names found in this base checkpoint.
    print(json.dumps({
        "target_module_count": len(targets),
        "target_module_examples": targets[:8],
        "key_mapping": QWEN35_KEY_MAPPING,
    }, indent=2), flush=True)

    processor_inputs = processor(text=[args.verify_prompt], return_tensors="pt")
    model_device = next(model.parameters()).device
    processor_inputs = {
        key: value.to(model_device) if hasattr(value, "to") else value
        for key, value in processor_inputs.items()
    }
    with torch.inference_mode():
        base_logits = model(**processor_inputs).logits[:, -1, :].float().cpu()

    print("Loading adapter with Qwen3.5 language-tower key remapping...", flush=True)
    peft_model = PeftModel.from_pretrained(
        model,
        str(args.adapter),
        config=config,
        is_trainable=False,
        key_mapping=QWEN35_KEY_MAPPING,
        autocast_adapter_dtype=False,
    )
    peft_model.eval()
    loaded_parameter_names = [name for name, _ in peft_model.named_parameters()]
    missing_targets = [
        target for target in targets
        if not any(
            name.endswith(f"{target}.lora_A.default.weight")
            for name in loaded_parameter_names
        )
        or not any(
            name.endswith(f"{target}.lora_B.default.weight")
            for name in loaded_parameter_names
        )
    ]
    if missing_targets:
        raise SystemExit(
            "adapter injection incomplete; missing LoRA A/B weights for "
            f"{len(missing_targets)} target modules, examples={missing_targets[:8]}"
        )
    with torch.inference_mode():
        adapted_logits = peft_model(**processor_inputs).logits[:, -1, :].float().cpu()

    delta = float((adapted_logits - base_logits).abs().max().item())
    if not math.isfinite(delta) or delta < args.min_logit_delta:
        raise SystemExit(
            f"adapter activation check failed: max absolute logit delta {delta!r} "
            f"is below required {args.min_logit_delta}; refusing to merge"
        )
    print(f"Adapter activation verified: max_abs_logit_delta={delta:.9g}", flush=True)

    print("Merging adapter and saving full multimodal checkpoint...", flush=True)
    merged = peft_model.merge_and_unload(safe_merge=True)
    args.output.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(
        str(args.output),
        safe_serialization=True,
        max_shard_size="5GB",
    )
    processor.save_pretrained(str(args.output))

    manifest = {
        "base_checkpoint": str(args.base.resolve()),
        "adapter": str(args.adapter.resolve()),
        "model_loader": "AutoModelForImageTextToText",
        "adapter_key_mapping": QWEN35_KEY_MAPPING,
        "language_target_module_count": len(targets),
        "activation_probe": {
            "method": "deterministic_last_token_logits",
            "prompt": args.verify_prompt,
            "max_absolute_logit_delta": delta,
            "minimum_required_delta": args.min_logit_delta,
        },
        "merge": "peft_merge_and_unload_safe",
        "processor_saved": True,
    }
    (args.output / "astrologically-intelligent-merge-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "merged", "output": str(args.output), "logit_delta": delta}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
