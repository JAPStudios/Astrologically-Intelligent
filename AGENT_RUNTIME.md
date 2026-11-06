# Agent runtime and provider configuration

Astrologically Intelligent provides persistent conversations, model tool calling, SQLite memory and work items, Markdown skills, an extensible Python plugin entry-point group, and a SQLite-backed multi-agent control plane.

## Setup

Python 3.10+; the core runtime uses the standard library.

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
| `openai-compatible` (default), `openai` | OpenAI Chat Completions | `ASTRO_AI_API_KEY`, `ASTRO_AI_BASE_URL`, `ASTRO_AI_MODEL` |
| `xai` / `grok` | OpenAI-compatible Chat Completions transport | `XAI_API_KEY`, default endpoint `https://api.x.ai/v1`, default model `grok-4.20-non-reasoning` |
| `perplexity` | Perplexity Chat Completions endpoint | `PERPLEXITY_API_KEY`, default endpoint `https://api.perplexity.ai`, default model `sonar` |
| `local` | OpenAI-compatible local endpoint | Set `ASTRO_AI_BASE_URL`; key may be empty for localhost |
| `anthropic` / `claude` | Native Anthropic Messages API | `ANTHROPIC_API_KEY` (or `ASTRO_AI_API_KEY`), optional `ANTHROPIC_BASE_URL`, `ASTRO_AI_MODEL` |
| `gemini` / `google` | Native Gemini `generateContent` API with function calling | `GEMINI_API_KEY` (or `ASTRO_AI_API_KEY`), optional `GEMINI_BASE_URL`, `ASTRO_AI_MODEL` |

Anthropic transport maps system messages, assistant tool-use blocks, tool schemas, and tool results to the runtime's function-tool interface. Gemini uses its native `generateContent` endpoint and preserves model-returned content, function-call IDs, and thought signatures across tool turns. xAI and Perplexity use the OpenAI-compatible transport.


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

The current `.gitmodules` inventory contains 742 pinned public repositories across all ten requested GitHub organizations, including five repositories from `herdrdev`. Retrieve pinned source trees with `git submodule update --init --recursive`. The inventory records upstream source references; it does not establish that every source tree has been retrieved, reviewed, built, or integrated into the application. Each candidate project still requires relevance, license, dependency, compatibility, implementation, and test review.
