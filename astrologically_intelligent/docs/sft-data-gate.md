# Supervised fine-tuning data gate

Before any SFT run, validate the immutable train, validation, and test JSONL
files with:

```sh
python scripts/validate_sft_splits.py \
  --train /path/to/train.jsonl \
  --validation /path/to/validation.jsonl \
  --test /path/to/test.jsonl \
  --output /path/to/split-validation.json
```

Each row must be a JSON object with a non-empty `messages` array. Messages
must use supported chat roles and text content. An assistant message may have
empty text only when it contains a non-empty, structurally valid `tool_calls`
array; tool-call arguments must decode to JSON objects. Tool-result messages
must include their `tool_call_id`. Each example must contain both a user input
and an assistant target. Stable family identity is read from `seed_family_id`
(at row level or inside `metadata`), `source_family_id`, `family_id`, or
`session_family_id`.

The gate rejects a family appearing in more than one split and rejects exact
conversation duplicates across splits after whitespace normalization. It
does not assign splits, infer family identity, redact private information,
judge answer correctness, or certify dataset rights/consent. Missing family
IDs therefore remain a provenance limitation and must be resolved by corpus
curation rather than assumed safe.

A valid report establishes only structural validity and the two tested
non-leakage properties. It does not establish that the data is representative,
high quality, safe, or sufficient to train the intended model.


Use `--require-family-id` for training candidates when every example must carry a stable family identifier. The gate checks structural tool-call validity; it does not prove that a tool call was executed successfully or that its result supports the assistant response.
