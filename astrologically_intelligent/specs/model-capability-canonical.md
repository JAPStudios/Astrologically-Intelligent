# Canonical Provider And Model Capability Layer

Last updated: dev@86b886c | 2026-10-14

## Scope

This spec covers the implementation introduced on current `dev` in:

- canonical model values and query helpers in `src/model_capabilities.py`;
- record, identity, and provider-detection helpers in
  `src/model_capability_readers/base.py`;
- reader dispatch in `src/model_capability_readers/__init__.py`;
- concrete readers for generic OpenAI-compatible, OpenAI, OpenRouter, Google,
  Anthropic, Hugging Face, Ollama, LM Studio, llama.cpp, and vLLM payloads;
- regression coverage in `tests/test_model_capabilities.py` and
  `tests/test_model_capability_readers.py`.

The reader modules normalize JSON returned by existing endpoint probes. The admin-only `GET /api/model-endpoints/{endpoint_id}/capabilities` route performs a fresh probe then returns canonical records without raw provider payloads. It captures native Anthropic and Google catalogues plus OpenAI-compatible and Ollama model-list responses. The route persists a non-empty observed catalogue as JSON on its `ModelEndpoint` row, with a Unix observation timestamp. A probe returning no model IDs or records leaves the previous snapshot intact. The admin endpoint settings UI renders the returned families, modalities, limits and capability tokens. Persisted records are not yet consumed by model routing or model pickers. OAuth-backed endpoints are not supported by this route.

There is no `src/provider_capability_schemas.py`, capability-specific diagnostics module, or runtime model-quirk registry on current `dev`.

## Layer Boundaries

- `src.model_capabilities` defines normalized families, tasks, modalities,
  capabilities, evidence sources/confidence, assertion states, deterministic
  controls, probe results, reasoning-control tokens, and display-surface
  queries.
- `ModelCapability` owns family, primary task, input/output modalities,
  capability tokens, limits, source, and confidence.
- `CapabilityAssertion` records claimed, verified, unsupported, or unknown
  status for one capability. Missing evidence is not an unsupported claim.
- `DeterministicControl` records support evidence for controls such as
  temperature, top-p, seed, tool choice, or prompt caching. A supported
  request control is not itself a model capability.
- `CapabilityProbeResult` is an in-memory evidence shape that converts pass,
  fail, or partial probe state into an assertion. The capability endpoint currently returns reader records without storing or merging probe assertions.
- `CapabilityQuery` and `display_surfaces_for()` map a normalized capability
  into candidate surfaces such as chat, vision chat, image generation,
  embeddings, or reranking. They are not wired into current pickers.
- Reader `ModelCapabilityRecord` binds a vendor/model identity to the nested
  capability object, assertions, deterministic controls, and optional raw
  provider evidence.

Provider transport support and per-model support are separate facts. Request and response adapters remain in `src.llm_core` and related provider modules. Model-specific observations remain in [model-quirks.md](model-quirks.md).

## Current Serialized Shapes

`ModelCapability.to_dict()` emits the nested capability shape:

```json
{
  "family": "chat",
  "primary_task": "chat.completions",
  "modalities": {
    "input": ["text", "image"],
    "output": ["text"]
  },
  "capabilities": ["tool_call", "vision"],
  "limits": {"context_tokens": 131072},
  "source": "provider_reader",
  "confidence": "provider_reported"
}
```

`ModelCapabilityRecord.to_dict()` wraps that value with `vendor`, `model_id`, `stable_model_id`, `display_name`, `capability_assertions`, and `deterministic_controls`. It does not currently emit a schema version or the flat `provider`/`model`/`features`/`controls` shape. Raw provider fields are included only when the caller passes `include_raw=True`.

Endpoint configuration can explicitly map `model_type=llm` to chat and `model_type=image` to image generation. Missing or unrecognized endpoint types stay unknown rather than silently becoming chat-capable in this schema layer.

## Identity And Reader Dispatch

`records_from_payload()` selects a reader from an explicit `vendor`, or from `detect_vendor(base_url, endpoint_kind)` when no vendor is supplied.

Current detection order and behavior are:

1. a recognized explicit endpoint kind;
2. label-bounded hostname checks for Hugging Face, OpenRouter, OpenAI, Anthropic, Google APIs, and Ollama Cloud;
3. common local ports: `11434` for Ollama, `1234` for LM Studio, `8000` for vLLM, and `30000` for SGLang;
4. generic OpenAI-compatible for any other parsed host, otherwise unknown.

These are normalization hints, not authorization. Hostname checks accept an exact domain or its dot-delimited subdomains after lowercasing and removing a trailing dot, so names such as `notopenai.com` do not match `openai.com`; local-port mappings remain intentionally covered by tests. Callers must not treat any result as proof of endpoint trust.

Implemented reader modules are `generic_openai`, `openai`, `openrouter`, `google`, `anthropic`, `huggingface`, `llamacpp`, `ollama`, `lmstudio`, and `vllm`. SGLang remains a placeholder vendor ID and dispatches through the generic identity-only reader. Other explicitly supplied vendor strings are also preserved while using that generic reader.

Stable model identity is scoped in this order:

- explicit endpoint ID;
- a short hash of normalized base URL when an endpoint ID is absent;
- `global` when neither endpoint identity is supplied.

## Generic Identity-Only Contract

The generic reader accepts mapping payloads containing `data[]` or `models[]`, plus bare lists. Each item must itself be a mapping and provide `id`, `name`, `model`, `key`, or `slug`. Duplicate model IDs within one payload are retained only once. These records remain identity-only; the reader does not infer capabilities from names or other descriptive fields.

The reader deliberately returns unknown family, modalities, capabilities, and controls. It preserves the raw item on the in-memory record but does not parse type/task fields, descriptions, ownership, supported-parameter lists, capability-looking booleans, or token limits.

## Provider-Native Readers

- OpenAI keeps the official Models API identity-only.
- Anthropic maps its native Messages API model list to text conversation support. The list does not establish vision, tool use, reasoning or context limits.
- Hugging Face maps explicit Hub `pipeline_tag` values to conservative task families and modalities. Only the `conversational` tag establishes chat; `text-generation` remains unknown-family text generation. `sentence-similarity` maps to classification rather than reranking because the task tag does not establish a dedicated reranking interface. Missing or unrecognized tags remain unknown.
- vLLM preserves an explicit `max_model_len` value as a context limit while leaving model family and capabilities unknown.
- OpenRouter maps explicit architecture modalities, supported parameters, limits, voices and default parameters into family/capability/control state.
- Google maps its native Models resource. The live endpoint probe captures all returned model metadata while preserving the existing chat-only model picker filter. Embedding-only methods map to the embedding family.
- Ollama maps native `/api/tags` payloads to identity-only records, accepts OpenAI-compatible `data[]` lists as identity-only records and maps selected-model `/api/show` capability tokens.
- LM Studio maps native v1 `models[]` and v0-style `data[]` fields. A plain OpenAI-compatible list without native type/capability fields stays unknown.
- llama.cpp can merge `/v1/models`, `/props` and `/slots` evidence for one served model. It records tool/streaming claims, explicit unsupported vision/audio assertions, controls and runtime/training/size limits.

Readers tolerate non-object entries and unknown fields where their helpers permit them. They do not infer authoritative capability from model IDs or display names.

## Evidence Semantics

The canonical vocabulary includes admin override, endpoint configuration, provider reader, Cookbook/Hugging Face, maintained registries, heuristic, probe, and unknown sources. It also defines explicit, provider-reported, registry, heuristic, and unknown confidence values.

Those tokens make evidence representable; current `dev` does not implement a global precedence, merge, expiry, or conflict-resolution engine. Assertions generated by readers are usually `claimed`; a `CapabilityProbeResult` maps pass to verified, fail to unsupported, and partial to claimed at the scope carried by that object.

## Tests

Focused tests pin:

- endpoint-kind, host and common-port vendor detection;
- endpoint/base-URL-scoped stable IDs;
- unknown behavior for generic and official OpenAI lists, including bare-list, `key`/`slug` identity, and duplicate identifiers;
- canonical normalization and display-surface matching;
- assertion, deterministic-control and probe-result shapes;
- OpenRouter, Google, Anthropic, Hugging Face, Ollama, LM Studio, llama.cpp and vLLM mappings;
- live Anthropic and Google metadata capture during endpoint probing;
- the admin capability route, including provider-managed authentication rejection;
- negative cases that avoid name-based media/capability inference.

The provider detector has narrow production consumers in `src/ai_interaction.py` and `routes/gallery/gallery_routes.py`. The canonical record readers now serve the admin capability endpoint plus its settings inspector. Model routing and model pickers do not yet consume these records.

## Current Gaps

- The admin capability endpoint persists the latest non-empty normalized catalogue on its endpoint row. Canonical records are not yet consumed by model routing, endpoint resolution, model context, request shaping or frontend pickers.
- Reader output is refreshed and persisted on explicit capability requests. Evidence merging, conflict resolution and expiry are not implemented.
- Provider detection still uses common-port hints; consumers must not promote normalization hints into trust decisions.
- Ten concrete readers exist; SGLang and other providers use the identity-only generic reader.
- Generic fallback accepts mapping payloads with `data[]` or `models[]`, plus bare lists; identity may come from `id`, `name`, `model`, `key`, or `slug`. These records remain identity-only and do not infer capabilities.
- There is no capability-specific diagnostic/logging path.
- Runtime request builders still contain model-name heuristics outside this canonical layer.
