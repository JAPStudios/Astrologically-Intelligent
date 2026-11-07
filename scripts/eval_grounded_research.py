"""Baseline evaluation for supplied-document research answering.

Default (offline): replays the scripted ``fake_answer`` of each synthetic case,
which checks the evaluation and citation-validation plumbing, not a model.

``--live``: sends the same cases to the provider configured by ASTRO_AI_* env
vars (default: a local Ollama-compatible endpoint you have installed yourself).
Only use --live with a provider you intend to call; cloud providers may charge.
This evaluates prompting + retrieval only; it does not train or change weights.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from astrologically_intelligent.grounded_research import answer_from_documents  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/grounded_research/synthetic_eval.json"


class ScriptedProvider:
    def __init__(self, answer: str): self.answer = answer
    def chat(self, messages, tools): return {"role": "assistant", "content": self.answer}


def score(case: dict, result: dict) -> bool:
    v, expect = result["validation"], case["expect"]
    if expect == "invalid":
        return not v["ok"]
    if expect == "insufficient":
        return v["ok"] and v["insufficient_evidence"]
    cited_ok = v["ok"] and not v["insufficient_evidence"] and set(case.get("must_cite", [])) <= set(v["cited"])
    if expect == "conflict":
        return cited_ok and "conflict" in result["answer"].lower()
    return cited_ok


def run(live: bool = False, fixture: Path = FIXTURE) -> list[dict]:
    data = json.loads(fixture.read_text())
    provider = None
    if live:
        from astrologically_intelligent.providers import provider_from_env
        provider = provider_from_env()
    rows = []
    for case in data["cases"]:
        if live and case["expect"] == "invalid":
            continue  # scripted-only case that checks the validator catches fabrication
        result = answer_from_documents(provider or ScriptedProvider(case["fake_answer"]),
                                       case["question"], data["documents"])
        rows.append({"case": case["name"], "passed": score(case, result), **result})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the configured ASTRO_AI provider")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    rows = run(args.live)
    for row in rows:
        print(f"{'PASS' if row['passed'] else 'FAIL'}  {row['case']}")
        if args.verbose or not row["passed"]:
            print(json.dumps({k: row[k] for k in ("answer", "validation")}, indent=2))
    print(f"{sum(r['passed'] for r in rows)}/{len(rows)} cases passed ({'live provider' if args.live else 'scripted offline answers'})")
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
