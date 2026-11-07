# Supplied-document research (opt-in)

`astrologically_intelligent/grounded_research.py` answers a question using only
documents you pass in, through the existing provider interface
(`provider.chat(messages, tools)`). It is separate from `AgentRuntime.chat`;
default chat behaviour and its system prompt are unchanged.

## What it does

1. Splits each document (`{"id", "title", "text"}`) into passages with stable
   citation IDs such as `[harbor-guide#p2]` (document ID + passage number).
   Inputs fail fast past fixed caps: 50 documents, 100,000 characters per
   document, 500,000 in total, single-line titles up to 200 characters,
   questions up to 2,000 characters, and a passage `limit` of 1-20 (a strict
   integer; booleans are rejected).
2. Picks the most relevant passages with simple word overlap (no extra
   dependencies, no embeddings). Unrelated passages are not sent.
3. Sends them, serialized as an escaped JSON array, with instructions to cite every factual sentence, never invent
   citations, use no outside knowledge, flag conflicting sources, and reply
   exactly `INSUFFICIENT_EVIDENCE` (nothing else) when the passages do not
   answer the question.
   No tools are offered to the model in this mode.
4. Validates the reply's structure: every sentence must end with one or more
   canonical known IDs (`[doc#p1]`, no leading zeros or variants); citations
   in the middle of a sentence, citation-only sentences, unknown or malformed
   IDs, and any abstention that is not exactly `INSUFFICIENT_EVIDENCE` are
   rejected. Abbreviations such as "e.g." split sentences and are rejected
   (fails closed).

```python
from astrologically_intelligent.grounded_research import answer_from_documents
from astrologically_intelligent.providers import provider_from_env
result = answer_from_documents(provider_from_env(), "When was it built?", documents)
```

## Limits

- Instructions reduce but do not guarantee accuracy.
- Validation checks citation *structure* only. It does not check semantic
  entailment: "built in 1902 by pirates [a#p1]" passes if `a#p1` exists. The
  evaluation keeps this as an explicit known-undetectable case.
- JSON serialization keeps document text inside quoted strings, as defence in
  depth. Documents can still contain text that tries to instruct the model,
  and no prompt format guarantees a model will ignore it.
- Word-overlap retrieval misses paraphrases and can match on shared names.
- Nothing is stored; there is no HTTP endpoint for this mode yet.

## Baseline evaluation

```sh
python -m unittest tests.test_grounded_research -v
python scripts/eval_grounded_research.py            # offline, scripted answers
python scripts/eval_grounded_research.py --live -v  # calls your configured ASTRO_AI_* provider
```

The offline run checks that each scripted good answer is accepted and each
scripted bad answer (uncited claims, abstention smuggling, mid-sentence or
non-canonical citations, fabricated IDs, one-sided conflict answers) is
rejected. It tests the checker, not a model. `--live`
measures a real model; use it only with a provider you intend to call (a local
Ollama model costs nothing; cloud providers may charge). The fixture in
`tests/fixtures/grounded_research/` is synthetic text about a fictional town,
covering a supported answer, insufficient evidence, conflicting sources, and a
fabricated citation.

## This is not fine-tuning

Retrieval, prompting and evaluation change what the model is *shown*, not the
model itself. Fine-tuning (for example LoRA) changes model weights, needs
training data, a GPU and its own evaluation. A live baseline from this script
is the evidence to decide whether fine-tuning is needed at all.
