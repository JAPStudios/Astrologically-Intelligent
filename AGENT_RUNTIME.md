# Agent runtime and provider configuration

Astrologically Intelligent provides persistent conversations, model tool calling, SQLite memory and work items, Markdown skills, an extensible Python plugin entry-point group, and a SQLite-backed multi-agent control plane.

## Setup

Python 3.10+; the core runtime uses the standard library.

The full FastAPI system is the primary interface and resolves models through its configured endpoint registry. The optional headless runtime exposes the same chat/session API without the web interface. It requires an explicit `ASTRO_AI_PROVIDER` value and provider-specific configuration; it does not silently default to Ollama or another provider.

| Provider value | Transport | Configuration |
| --- | --- | --- |
| `openai` / `chat-completions` | OpenAI Chat Completions | `ASTRO_AI_API_KEY`, optional `ASTRO_AI_BASE_URL`, `ASTRO_AI_MODEL` |
| `anthropic` / `claude` | Native Anthropic Messages API | `ANTHROPIC_API_KEY` (or `ASTRO_AI_API_KEY`), optional `ANTHROPIC_BASE_URL`, `ASTRO_AI_MODEL` |
| `gemini` / `google` | Native Gemini `generateContent` API with function calling | `GEMINI_API_KEY` (or `ASTRO_AI_API_KEY`), optional `GEMINI_BASE_URL`, `ASTRO_AI_MODEL` |
| `xai` / `grok` | xAI Chat Completions transport | `XAI_API_KEY` (or `ASTRO_AI_API_KEY`), default endpoint `https://api.x.ai/v1`, default model `grok-4.20-non-reasoning` |
| `perplexity` | Perplexity Chat Completions transport | `PERPLEXITY_API_KEY` (or `ASTRO_AI_API_KEY`), default endpoint `https://api.perplexity.ai`, default model `sonar` |
| `local` | Local OpenAI-compatible endpoint | Explicitly set `ASTRO_AI_BASE_URL` and `ASTRO_AI_MODEL`; no API key is required for loopback |

The full web system's default endpoint is managed in its endpoint registry. The headless provider variable is an override for the standalone entry point and is not the default-selection mechanism for the full web system. Anthropic maps Messages API system messages, assistant tool-use blocks, tool schemas and tool results to the runtime's function-tool interface. Gemini uses its native `generateContent` endpoint and preserves model-returned content, function-call IDs and thought signatures across tool turns. xAI and Perplexity use the Chat Completions request format.

## HTTP service

The service binds to `127.0.0.1:8765` by default. It exposes `GET /health`, authenticated `GET /v1/history?session_id=...`, `GET /v1/sessions`, authenticated `DELETE /v1/sessions/{session_id}` and `POST /v1/chat`. Conversation deletion removes only messages belonging to the selected session and returns 404 when that session has no messages. Conversation history returns up to 200 messages (40 by default) in chronological order. Non-loopback binding requires `ASTRO_AI_API_TOKEN` with at least 24 characters; clients authenticate with a bearer token. Request bodies are limited to 1 MB. A supplied `session_id` must contain 1–128 ASCII letters, digits, underscores, or hyphens; invalid identifiers are rejected with HTTP 400 before the model runtime is invoked.

## Runtime tools

- Memory: `memory.remember`, `memory.recall`, `memory.forget` (exact namespace and key)
- Work items: `work.create`, `work.list`, `work.update`
- Skills: `skills.list`, `skills.read`
- Agents: `agents.register`, `agents.list`, `agents.execute` (active model-backed agents), `agents.set_state`, `agents.due`

Model-backed agents may declare `allowed_tools` in their registration config. Only those exact registered tool names are exposed to the model. The default is an empty allowlist. Set `max_tool_rounds` from 0 to 12 (default 4) to bound tool-call cycles. Agent execution records each tool result in its run output; nested agent execution and direct run-management tools are not permitted. Agents may also declare `skills` as a list of installed skill names; their instructions are loaded into the agent system context, with a combined 128 KiB limit.
- Goals: `goals.create`, `goals.list`
- Approvals: `approvals.request`, `approvals.list`, `approvals.decide`
- Budgets: `budgets.set`, `budgets.record_cost`, `budgets.list`
- Runs: `runs.start`, `runs.finish`
- Plugins: `plugins.discover`, `plugins.status`


## Plugins

Installed Python distributions may register entry points under `astrologically_intelligent.plugins`. Each entry point must load an object exposing `setup(registry)`. Plugins are executable trusted code; install only reviewed packages.

## Tests

```sh
python -m unittest discover -s tests -v
```

Upstream implementation coverage and outstanding service interfaces are documented in `UPSTREAM_IMPORT.md`. Source references are not counted as completed runtime features.
