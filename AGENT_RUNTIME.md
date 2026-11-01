# Agent runtime and provider configuration

Astrologically Intelligent provides a persistent conversation runtime with model tool calling, SQLite memory and work items, Markdown skills, an extensible Python plugin entry-point group, and a SQLite-backed agent control plane.

## Setup

Python 3.10+; the core runtime uses the standard library. No provider SDK is required for the HTTP transports.

```sh
export ASTRO_AI_PROVIDER=openai-compatible
export ASTRO_AI_API_KEY="..."
export ASTRO_AI_MODEL="gpt-4.1-mini"
export ASTRO_AI_BASE_URL="https://api.openai.com/v1"
python -m astrologically_intelligent
```

Provider selection is controlled by `ASTRO_AI_PROVIDER`:

| Provider value | Transport | Configuration |
| --- | --- | --- |
| `openai-compatible` (default) | OpenAI Chat Completions | `ASTRO_AI_API_KEY`, `ASTRO_AI_BASE_URL`, `ASTRO_AI_MODEL` |
| `openai` | OpenAI Chat Completions | Same as above |
| `xai` / `grok` | OpenAI-compatible Chat Completions | Set base URL and xAI key/model |
| `perplexity` | OpenAI-compatible Chat Completions transport | Configure an endpoint/model that supports the Chat Completions tool schema |
| `local` | OpenAI-compatible local endpoint | Set `ASTRO_AI_BASE_URL`; API key may be empty for localhost |
| `anthropic` / `claude` | Native Anthropic Messages API | `ANTHROPIC_API_KEY` (or `ASTRO_AI_API_KEY`), optional `ANTHROPIC_BASE_URL`, `ASTRO_AI_MODEL` |

Anthropic transport maps system messages, assistant tool-use blocks, tool schemas, and tool results to and from the runtime's function-tool interface. xAI and other compatible providers use the existing Chat Completions transport. This does not claim native integration of every vendor SDK or every vendor-specific endpoint.

## HTTP service

The service binds to `127.0.0.1:8765` by default. It exposes `GET /health` and `POST /v1/chat`. Non-loopback binding requires `ASTRO_AI_API_TOKEN` with at least 24 characters; clients authenticate with a bearer token. Request bodies are limited to 1 MB.

## Runtime tools

- Memory: `memory.remember`, `memory.recall`
- Work items: `work.create`, `work.list`, `work.update`
- Skills: `skills.list`, `skills.read`
- Agents: `agents.register`, `agents.list`, `agents.set_state`, `agents.due`
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

The current source integrations are incremental. The presence of a provider adapter or an upstream reference does not mean every upstream project has been imported or ported.
