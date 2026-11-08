#!/usr/bin/env python3
"""Verify that a served merged Qwen3.5 checkpoint differs from its base model.

Both model IDs are queried through the same OpenAI-compatible endpoint with
identical deterministic requests. The check requires usable token logprobs and
a measurable difference on multiple shared top-token candidates.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_top_logprobs(response: dict) -> tuple[str, dict[str, float]]:
    try:
        choice = response["choices"][0]
        content = choice["logprobs"]["content"]
        first = content[0]
        token = first["token"]
        candidates = first["top_logprobs"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("endpoint did not return first-token top_logprobs") from exc
    if not isinstance(token, str) or not isinstance(candidates, list):
        raise ValueError("endpoint returned malformed first-token logprobs")
    parsed: dict[str, float] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("token"), str):
            continue
        value = candidate.get("logprob")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            parsed[candidate["token"]] = float(value)
    if token not in parsed:
        value = first.get("logprob")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            parsed[token] = float(value)
    if not parsed:
        raise ValueError("endpoint returned no numeric top-token logprobs")
    return token, parsed


def compare_logprobs(
    base: dict[str, float], merged: dict[str, float], minimum_delta: float
) -> dict:
    shared = sorted(set(base) & set(merged))
    if len(shared) < 3:
        raise ValueError(
            f"only {len(shared)} shared top-token candidates; increase top_logprobs "
            "or use a compatible serving endpoint"
        )
    deltas = {token: abs(base[token] - merged[token]) for token in shared}
    maximum = max(deltas.values())
    changed = sum(delta >= minimum_delta for delta in deltas.values())
    if maximum < minimum_delta or changed < 2:
        raise ValueError(
            "merged model appears identical to base within the requested "
            f"tolerance: max_delta={maximum:.9g}, changed_candidates={changed}"
        )
    return {
        "shared_candidates": len(shared),
        "changed_candidates": changed,
        "max_absolute_logprob_delta": maximum,
        "minimum_delta": minimum_delta,
    }


def request_logprobs(
    endpoint: str, model: str, prompt: str, api_key: str, timeout: float
) -> tuple[str, dict[str, float]]:
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 1,
        "logprobs": True,
        "top_logprobs": 20,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"serving endpoint returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"serving endpoint request failed: {type(exc).__name__}") from exc
    return parse_top_logprobs(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible API base, including /v1")
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--merged-model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--min-logprob-delta", type=float, default=1e-4)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args(argv)
    if not args.base_url.rstrip("/").endswith("/v1"):
        parser.error("--base-url must end in /v1")
    if not args.prompt.strip():
        parser.error("--prompt must contain text")
    if not math.isfinite(args.min_logprob_delta) or args.min_logprob_delta <= 0:
        parser.error("--min-logprob-delta must be finite and positive")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")

    key = os.getenv(args.api_key_env, "")
    try:
        base_token, base_values = request_logprobs(
            args.base_url, args.base_model, args.prompt, key, args.timeout
        )
        merged_token, merged_values = request_logprobs(
            args.base_url, args.merged_model, args.prompt, key, args.timeout
        )
        comparison = compare_logprobs(
            base_values, merged_values, args.min_logprob_delta
        )
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"serving verification failed: {exc}") from exc

    report = {
        "status": "different",
        "base_model": args.base_model,
        "merged_model": args.merged_model,
        "base_first_token": base_token,
        "merged_first_token": merged_token,
        **comparison,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
