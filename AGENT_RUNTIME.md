# Agent runtime and provider configuration

Astrologically Intelligent provides persistent conversations, model tool calling, SQLite memory and work items, Markdown skills, an extensible Python plugin entry-point group, and a SQLite-backed multi-agent control plane.

## Setup

Python 3.10+; the core runtime uses the standard library.

```sh
# Start Ollama locally and install a model before launching the runtime.
# Set ASTRO_AI_MODEL to the exact identifier shown by: ollama list
export ASTRO_AI_PROVIDER=local
export ASTRO_AI_BASE_URL="http://127.0.0.1:11434/v1"
export ASTRO_AI_MODEL="YOUR_INSTALLED_MODEL"
python -m astrologically_intelligent
```

Provider selection is controlled by `ASTRO_AI_PROVIDER`. A fresh installation defaults to a local Ollama-compatible endpoint; it does not silently send prompts to a competing cloud provider.

| Provider value | Transport | Configuration |
| --- | --- | --- |
| `local` (default) | Local OpenAI-compatible endpoint; defaults to Ollama at `http://127.0.0.1:11434/v1` | Install a local model and set `ASTRO_AI_MODEL` to its exact identifier; no API key is required for loopback |
| `openai` / `chat-completions` | OpenAI Chat Completions | Explicit opt-in; `ASTRO_AI_API_KEY`, `ASTRO_AI_BASE_URL`, `ASTRO_AI_MODEL` |
| `xai` / `grok` | Chat Completions request format | Explicit opt-in; `XAI_API_KEY`, default endpoint `https://api.x.ai/v1`, default model `grok-4.20-non-reasoning` |
| `perplexity` | Perplexity Chat Completions endpoint | Explicit opt-in; `PERPLEXITY_API_KEY`, default endpoint `https://api.perplexity.ai`, default model `sonar` |
| `anthropic` / `claude` | Native Anthropic Messages API | Explicit opt-in; `ANTHROPIC_API_KEY` (or `ASTRO_AI_API_KEY`), optional `ANTHROPIC_BASE_URL`, `ASTRO_AI_MODEL` |
| `gemini` / `google` | Native Gemini `generateContent` API with function calling | Explicit opt-in; `GEMINI_API_KEY` (or `ASTRO_AI_API_KEY`), optional `GEMINI_BASE_URL`, `ASTRO_AI_MODEL` |

The local runtime uses an OpenAI-compatible local inference endpoint. The local model is still a separately installed model; this configuration does not claim that Astrologically Intelligent already contains a trained proprietary foundation model. Cloud provider transports are optional compatibility routes, not the product's required intelligence engine. Anthropic maps system messages, assistant tool-use blocks, tool schemas, and tool results to the runtime's function-tool interface. Gemini uses its native `generateContent` endpoint and preserves model-returned content, function-call IDs, and thought signatures across tool turns. xAI and Perplexity use the Chat Completions request format.


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

The current `.gitmodules` inventory contains 742 pinned public repositories across the original ten organizations, including five repositories from `herdrdev`. The requested source scope is twenty organizations. The importer now also covers Cursor, DeepSeek AI, LukaLabs, Meta Llama plus AI-query results from Apple, AWS, Brave, Google, Kagi Search, and Microsoft. The import workflow adds their Gitlinks in bounded batches after the importer update is merged. Retrieve pinned source trees with `git submodule update --init --recursive`. The inventory records upstream source references; it does not establish that every source tree has been retrieved, reviewed, built, or integrated into the application. Each candidate project still requires relevance, license, dependency, compatibility, implementation, and test review.
