# Model adapter activation verification

Use `scripts/verify_model_adapter.py` before evaluating or promoting a LoRA
adapter served through an OpenAI-compatible chat-completions endpoint. A model
appearing in `/v1/models`, a successful HTTP response or a different adapter
file does not prove that the adapter affects inference.

The verifier sends the same prompts to the base and candidate models with
`temperature=0`, `max_tokens=1`, `logprobs=true` and top-token log-probabilities.
Thinking is disabled by default through
`chat_template_kwargs.enable_thinking=false`. It compares token identities
and log-probabilities for the first generated token.

Example:

```sh
python scripts/verify_model_adapter.py \
  --base-url http://127.0.0.1:18051/v1 \
  --candidate-url http://127.0.0.1:18052/v1 \
  --base-model qwen35-9b-base \
  --candidate-model qwen35-9b-tool-router \
  --output data/evals/adapter-activation.json
```

Use `--prompt` repeatedly to supply a custom probe set. By default, the script
uses four short tool-selection prompts. Set `--base-api-key-env` and
`--candidate-api-key-env` to environment-variable names when either endpoint
requires bearer authentication; key values are never written to the report.

The default classification requires at least three identical probes before
reporting an inactive adapter and at least two differing probes before
reporting that the candidate differs from the base. Smaller or mixed probe
sets are inconclusive. Adjust `--minimum-probes`,
`--minimum-different-prompts` and `--tolerance` only when the evaluation
protocol justifies doing so.

Exit codes:

- `0`: candidate distributions differ from the base on the required number of prompts
- `1`: all required probe distributions are identical; adapter activation was not observed
- `2`: insufficient or mixed evidence
- `3`: request or response validation failed

A differing distribution establishes only that the candidate behaves
differently on the tested prompts. It does not establish better tool selection,
argument accuracy, response quality, safety or production readiness. Those
require a separate held-out evaluation against the actual application runtime.
