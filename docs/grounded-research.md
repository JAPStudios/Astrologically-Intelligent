# Supplied-document research (opt-in)

`astrologically_intelligent/grounded_research.py` answers a question using only
documents you pass in, through the existing provider interface
(`provider.chat(messages, tools)`). It is separate from `AgentRuntime.chat`;
default chat behaviour and its system prompt are unchanged.

## What it does

1. Splits each document (`{"id", "title", "text"}`) into passages with stable
   citation IDs such as `[harbor-guide#p2]` (document ID + passage number).
2. Picks the most relevant passages with simple word overlap (no extra
   dependencies, no embeddings). Unrelated passages are not sent.
3. Sends them with instructions to cite every factual sentence, never invent
   citations, use no outside knowledge, flag conflicting sources, and reply
   `INSUFFICIENT_EVIDENCE` when the passages do not answer the question.
   No tools are offered to the model in this mode.
4. Validates the reply: unknown or malformed citation IDs and uncited
   factual sentences are reported in `validation`.

```python
from astrologically_intelligent.grounded_research import answer_from_documents
from astrologically_intelligent.providers import provider_from_env
result = answer_from_documents(provider_from_env(), "When was it built?", documents)
```

## Limits

- Instructions reduce but do not guarantee accuracy. Validation checks
  citation *structure*; it cannot prove a cited passage supports a claim.
- Word-overlap retrieval misses paraphrases and can match on shared names.
- Nothing is stored; there is no HTTP endpoint for this mode yet.

## Baseline evaluation

```sh
python -m unittest tests.test_grounded_research -v
python scripts/eval_grounded_research.py            # offline, scripted answers
python scripts/eval_grounded_research.py --live -v  # calls your configured ASTRO_AI_* provider
```

The offline run checks the evaluation and validation plumbing only. `--live`
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
