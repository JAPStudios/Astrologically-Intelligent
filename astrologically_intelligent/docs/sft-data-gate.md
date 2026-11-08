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

## Converting approved source traces

The expansion split builder writes source-trace rows (`user`, `assistant`,
`tool_events`), not chat-training examples. Convert an approved text-only trace
file explicitly:

```sh
python scripts/convert_sft_traces_to_messages.py \
  --input /path/to/approved-trace.jsonl \
  --output /path/to/messages.jsonl
```

The converter requires a non-empty session ID, user and assistant text, a
stable seed-family ID, and an explicit `train`, `validation`, or `test`
assignment. It preserves source metadata and family identity and writes
newline-terminated JSONL. It refuses any row with tool events because the
tracked source-trace schema does not establish a reliable mapping from those
events to assistant tool-call IDs, function arguments, and tool-result
messages. It does not invent those records. Tool-bearing traces require a
separately verified schema adapter before they can enter chat SFT.

The converter is a format bridge, not a data approval mechanism. Only already
approved source traces should be passed to it. Run the split validator across
the resulting train, validation, and test files before training.

The optional `--expected-split` flag makes each conversion reject rows assigned
to a different partition. Convert the builder's three outputs separately:

```sh
python scripts/convert_sft_traces_to_messages.py --input /path/to/source/train.jsonl --output /path/to/chat/train.jsonl --expected-split train
python scripts/convert_sft_traces_to_messages.py --input /path/to/source/validation.jsonl --output /path/to/chat/validation.jsonl --expected-split validation
python scripts/convert_sft_traces_to_messages.py --input /path/to/source/test.jsonl --output /path/to/chat/test.jsonl --expected-split test
```

Then validate those three chat files with `validate_sft_splits.py --require-family-id`.

## Qwen3.5 multimodal LoRA merge

The optional model-training dependencies are isolated in `requirements-sft.txt`.
Install PyTorch separately for the target accelerator, then install that file.
The application runtime requirements are intentionally not expanded by the
training stack.

The tracked merge entry point reproduces the Qwen3.5 text-adapter to full
multimodal-checkpoint path recorded in the training ledger:

```sh
python scripts/merge_hf_lora.py \
  --base /path/to/Qwen3.5-9B \
  --adapter /path/to/final_adapter \
  --output /path/to/merged-full-bf16 \
  --verify-prompt "Select the appropriate tool for this request."
```

The merge requires a local full Qwen3.5 checkpoint and a PEFT adapter. It
loads the full model with `AutoModelForImageTextToText`, limits adapter
targets to explicitly matched language-tower modules, remaps causal adapter
keys from `model.layers` to `model.language_model.layers`, checks that every
target has both LoRA A and B weights, and compares deterministic base and
adapter logits. It refuses to save if the adapter has no measurable effect.
The processor is saved alongside the merged checkpoint, and a manifest
records the inputs and activation measurement.

This is a reproducible merge and activation gate, not a training run or a
production deployment. The merge must still be run against the actual approved
adapter and base checkpoint, then the resulting full checkpoint must pass the
serving-side log-probability check and held-out tool-routing evaluation.
