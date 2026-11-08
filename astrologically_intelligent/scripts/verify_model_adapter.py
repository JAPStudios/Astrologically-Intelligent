#!/usr/bin/env python3
"""Check whether an OpenAI-compatible candidate model changes token log-probabilities.

A model appearing in /v1/models or returning HTTP 200 does not prove that a
LoRA adapter is active. This probe compares deterministic top-token
log-probabilities from the base and candidate models on identical prompts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_PROMPTS = (
    "A user asks to list saved notes. Return the single best tool name.",
    "A user asks for current information from the web. Return the single best tool name.",
    "A user asks to create a calendar event at a specified time. Return the single best tool name.",
    "A user asks to list saved documents. Return the single best tool name.",
)
SYSTEM_PROMPT = "Choose the next tool for the assistant. Return only the tool name, without explanation."


def _top_logprobs(payload: dict[str, Any]) -> list[tuple[str, float]]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("completion response has no choices[0]")
    logprobs = choices[0].get("logprobs")
    if not isinstance(logprobs, dict):
        raise ValueError("completion response omitted logprobs")
    content = logprobs.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise ValueError("completion response omitted first-token logprobs")
    top = content[0].get("top_logprobs")
    if not isinstance(top, list) or not top:
        raise ValueError("completion response omitted first-token top_logprobs")
    result = []
    for item in top:
        if not isinstance(item, dict):
            raise ValueError("malformed top_logprobs entry")
        token = item.get("token")
        value = item.get("logprob")
        if not isinstance(token, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("malformed token/logprob value")
        result.append((token, float(value)))
    return result


def compare_distributions(
    base: list[tuple[str, float]], candidate: list[tuple[str, float]], tolerance: float
) -> dict[str, Any]:
    base_map = dict(base)
    candidate_map = dict(candidate)
    same_tokens = set(base_map) == set(candidate_map)
    differences = {
        token: abs(base_map[token] - candidate_map[token])
        for token in set(base_map).intersection(candidate_map)
    }
    max_difference = max(differences.values()) if differences else None
    identical = same_tokens and len(base_map) == len(candidate_map) and all(
        difference <= tolerance for difference in differences.values()
    )
    return {
        "identical": identical,
        "same_top_tokens": same_tokens,
        "max_absolute_logprob_difference": max_difference,
        "base_top_logprobs": [{"token": token, "logprob": value} for token, value in base],
        "candidate_top_logprobs": [{"token": token, "logprob": value} for token, value in candidate],
    }


def _request_logprobs(
    client: httpx.Client,
    base_url: str,
    model: str,
    prompt: str,
    *,
    api_key: str,
    timeout: float,
    top_logprobs: int,
    disable_thinking: bool,
) -> list[tuple[str, float]]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1,
        "logprobs": True,
        "top_logprobs": top_logprobs,
        "stream": False,
    }
    if disable_thinking:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    response = client.post(
        base_url.rstrip("/") + "/chat/completions",
        json=body,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    return _top_logprobs(response.json())


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    base_key = os.environ.get(args.base_api_key_env, "") if args.base_api_key_env else ""
    candidate_key = os.environ.get(args.candidate_api_key_env, "") if args.candidate_api_key_env else ""
    prompts = args.prompt or list(DEFAULT_PROMPTS)
    records = []
    with httpx.Client() as client:
        for index, prompt in enumerate(prompts, 1):
            base = _request_logprobs(
                client, args.base_url, args.base_model, prompt,
                api_key=base_key, timeout=args.timeout,
                top_logprobs=args.top_logprobs, disable_thinking=args.disable_thinking,
            )
            candidate = _request_logprobs(
                client, args.candidate_url, args.candidate_model, prompt,
                api_key=candidate_key, timeout=args.timeout,
                top_logprobs=args.top_logprobs, disable_thinking=args.disable_thinking,
            )
            comparison = compare_distributions(base, candidate, args.tolerance)
            records.append({"prompt_index": index, "prompt": prompt, **comparison})

    identical = sum(record["identical"] for record in records)
    different = len(records) - identical
    if identical == len(records) and len(records) >= args.minimum_probes:
        status = "inactive"
        exit_code = 1
    elif different >= args.minimum_different_prompts:
        status = "different"
        exit_code = 0
    else:
        status = "inconclusive"
        exit_code = 2
    return {
        "status": status,
        "base_model": args.base_model,
        "candidate_model": args.candidate_model,
        "prompts_tested": len(records),
        "identical_prompts": identical,
        "different_prompts": different,
        "tolerance": args.tolerance,
        "records": records,
        "exit_code": exit_code,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible base-model /v1 URL")
    parser.add_argument("--candidate-url", required=True, help="OpenAI-compatible candidate /v1 URL")
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--candidate-model", required=True)
    parser.add_argument("--prompt", action="append", help="Probe prompt; repeat for multiple prompts")
    parser.add_argument("--base-api-key-env", default="")
    parser.add_argument("--candidate-api-key-env", default="")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--top-logprobs", type=int, default=5)
    parser.add_argument("--tolerance", type=float, default=1e-8)
    parser.add_argument("--minimum-different-prompts", type=int, default=2)
    parser.add_argument("--minimum-probes", type=int, default=3)
    parser.add_argument("--disable-thinking", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.top_logprobs <= 20:
        parser.error("--top-logprobs must be between 1 and 20")
    if args.timeout <= 0 or args.tolerance < 0:
        parser.error("--timeout must be positive and --tolerance non-negative")
    if args.minimum_different_prompts < 1 or args.minimum_probes < 2:
        parser.error("--minimum-different-prompts must be positive and --minimum-probes at least 2")
    try:
        report = run_probe(args)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        print(f"adapter verification failed: {exc}", file=sys.stderr)
        return 3
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
