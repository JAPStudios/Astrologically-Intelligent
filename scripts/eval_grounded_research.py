"""Baseline evaluation for supplied-document research answering.

Default (offline): for each synthetic case, checks that the scripted good
answer is accepted and that every scripted bad answer is rejected. This tests
the scoring and citation-validation logic, not a model. Bad answers marked
``known_undetectable`` document what structural checks cannot catch; they are
reported, not counted as failures.

``--live``: sends each question to the provider configured by ASTRO_AI_* env
vars (default: a local Ollama-compatible endpoint you installed yourself) and
scores the real answer. Only use --live with a provider you intend to call;
cloud providers may charge. This evaluates prompting + retrieval only; it does
not train or change model weights.
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
    """True when the answer meets the case's structural expectation."""
    v, expect = result["validation"], case["expect"]
    if not v["ok"]:
        return False
    if expect == "insufficient":
        return v["insufficient_evidence"]
    if v["insufficient_evidence"] or not set(case.get("must_cite", [])) <= set(v["cited"]):
        return False
    if expect == "conflict":
        return len({cid.split("#")[0] for cid in v["cited"]}) >= 2
    return True


def _run_one(provider, case, documents):
    return answer_from_documents(provider, case["question"], documents)


def run(live: bool = False, fixture: Path = FIXTURE) -> list[dict]:
    data = json.loads(fixture.read_text())
    rows = []
    if live:
        from astrologically_intelligent.providers import provider_from_env
        provider = provider_from_env()
        for case in data["cases"]:
            result = _run_one(provider, case, data["documents"])
            rows.append({"case": case["name"], "kind": "live", "passed": score(case, result), **result})
        return rows
    for case in data["cases"]:
        result = _run_one(ScriptedProvider(case["good_answer"]), case, data["documents"])
        rows.append({"case": case["name"], "kind": "good", "passed": score(case, result), **result})
        for bad in case.get("bad_answers", []):
            result = _run_one(ScriptedProvider(bad["answer"]), case, data["documents"])
            rejected = not score(case, result)
            kind = "known_undetectable" if bad.get("known_undetectable") else "bad"
            rows.append({"case": f"{case['name']} / {bad['why']}", "kind": kind,
                         "passed": rejected if kind == "bad" else True,
                         "rejected": rejected, **result})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the configured ASTRO_AI provider")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    rows = run(args.live)
    for row in rows:
        label = "NOTE" if row["kind"] == "known_undetectable" else ("PASS" if row["passed"] else "FAIL")
        extra = f" (rejected={row['rejected']})" if row["kind"] == "known_undetectable" else ""
        print(f"{label}  [{row['kind']}] {row['case']}{extra}")
        if args.verbose or not row["passed"]:
            print(json.dumps({k: row[k] for k in ("answer", "validation")}, indent=2))
    scored = [r for r in rows if r["kind"] != "known_undetectable"]
    print(f"{sum(r['passed'] for r in scored)}/{len(scored)} checks passed "
          f"({'live provider' if args.live else 'scripted offline answers'}); "
          f"{len(rows) - len(scored)} known-undetectable case(s) reported")
    return 0 if all(r["passed"] for r in scored) else 1


if __name__ == "__main__":
    raise SystemExit(main())
