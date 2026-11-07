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
| `deepseek` / `deepseek-ai` | OpenAI-compatible Chat Completions API with native function calling | Explicit opt-in; `DEEPSEEK_API_KEY` (or `ASTRO_AI_API_KEY`), optional `DEEPSEEK_BASE_URL` or `ASTRO_AI_BASE_URL`, `ASTRO_AI_MODEL` (default `deepseek-chat`) |
| `azure` / `azure-openai` / `microsoft-foundry` | Azure OpenAI / Microsoft Foundry OpenAI v1 Chat Completions API with native function calling | Explicit opt-in; `AZURE_OPENAI_API_KEY` or `AZURE_INFERENCE_CREDENTIAL`, `AZURE_OPENAI_ENDPOINT` or `AZURE_AI_ENDPOINT`, deployment in `AZURE_OPENAI_DEPLOYMENT` or `ASTRO_AI_MODEL` |

The local runtime uses an OpenAI-compatible local inference endpoint. The local model is still a separately installed model; this configuration does not claim that Astrologically Intelligent already contains a trained proprietary foundation model. Cloud provider transports are optional compatibility routes, not the product's required intelligence engine. DeepSeek uses the same validated Chat Completions transport as OpenAI-compatible endpoints, preserving native function-call IDs, argument payloads, and tool results across turns. Anthropic maps system messages, assistant tool-use blocks, tool schemas, and tool results to the runtime's function-tool interface. Gemini uses its native `generateContent` endpoint and preserves model-returned content, function-call IDs, and thought signatures across tool turns. xAI and Perplexity use the Chat Completions request format.


## Service integration contracts

### CatChat

CatChat's output boundary is the authenticated root-runtime endpoint `POST /v1/chat`. Send a JSON object containing `message` plus an optional `session_id`; the response contains `session_id` plus `response`. The endpoint uses the same configured model provider, persistent session store, native tool registry, and tool-round limits as the local agent runtime. A non-loopback deployment requires `ASTRO_AI_API_TOKEN` with at least 24 characters. Keep the bearer token in CatChat's trusted server process, never in browser JavaScript.

This repository supplies the backend API contract. The separate CatChat client implementation is not present in this repository, so this documentation does not claim a live CatChat deployment connection. The full FastAPI web application has a separate `/api/chat` surface; it is not the root-runtime API described here.

### Peanut Browsing

The full web application registers `web_search` for Peanut Browsing's first-party index plus `peanut_browsing_crawl` for submitting public sites to that index. Configure `PEANUT_SEARCH_API_URL` plus `PEANUT_SEARCH_API_KEY`. The gateway must use HTTPS outside loopback development. Search returns only indexed pages; an unavailable or empty index does not silently fall back to another search provider. Release smoke uses a deterministic loopback gateway fixture; it verifies the tool cycle, not broad live-web coverage.

### PanMedia

PanMedia's agent-management integration uses the authenticated `/v1/agents`, `/v1/goals`, `/v1/approvals`, `/v1/budgets`, and `/v1/runs` routes documented below. These routes expose the existing orchestration store; they do not create a second agent database. Keep the bearer token in a trusted PanMedia server process, never in browser JavaScript.

## HTTP service

The service binds to `127.0.0.1:8765` by default. It exposes public `GET /health`, authenticated `GET /v1/history?session_id=...`, `GET /v1/sessions`, `DELETE /v1/sessions/{session_id}`, and `POST /v1/chat`. The authenticated agent-management API also exposes `GET/POST /v1/agents`, `GET /v1/agents/{agent_id}`, `PATCH /v1/agents/{agent_id}`, `POST /v1/agents/{agent_id}/heartbeat`, `POST /v1/agents/{agent_id}/execute`, goal and approval routes, budget routes, plus `GET /v1/runs/{run_id}`. Conversation deletion removes only messages belonging to the selected session and returns 404 when that session has no messages. Conversation history returns up to 200 messages (40 by default) in chronological order. Non-loopback binding requires `ASTRO_AI_API_TOKEN` with at least 24 characters; clients authenticate with a bearer token. Request bodies are limited to 1 MB. A supplied `session_id` must contain 1–128 ASCII letters, digits, underscores, or hyphens; invalid identifiers are rejected with HTTP 400 before the model runtime is invoked.

## Authenticated agent-management API

The loopback HTTP service exposes the same SQLite-backed orchestration control plane used by native agent tools. PanMedia or another trusted server-side client can manage agents with the bearer token configured as `ASTRO_AI_API_TOKEN`. Keep this API on loopback or behind an HTTPS reverse proxy; do not place the token in browser JavaScript.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/agents` | List agents; optional `?state=active`, `paused`, or `disabled` |
| `GET` | `/v1/agents/{agent_id}` | Retrieve one registered agent |
| `GET` | `/v1/agents/{agent_id}` | Retrieve one registered agent |
| `GET` | `/v1/agents/due` | List agents whose heartbeat is due |
| `POST` | `/v1/agents/{agent_id}/heartbeat` | Mark an active agent heartbeat |
| `POST` | `/v1/agents` | Register an agent with `name`, `adapter`, optional `model`, `role`, `config`, and `heartbeat_seconds` |
| `PATCH` | `/v1/agents/{agent_id}` | Set an agent's state to `active`, `paused`, or `disabled` |
| `POST` | `/v1/agents/{agent_id}/execute` | Execute a prompt with an active model-backed agent |
| `GET` | `/v1/goals` | List goals; optional status filter |
| `POST` | `/v1/goals` | Create a goal |
| `GET` | `/v1/approvals?status=pending` | List approval requests |
| `POST` | `/v1/approvals` | Create an approval request |
| `POST` | `/v1/approvals/{approval_id}/decision` | Approve, reject, or cancel a pending request |
| `GET` | `/v1/budgets` | List organization and agent budgets |
| `POST` | `/v1/budgets` | Set a budget |
| `POST` | `/v1/budgets/costs` | Record cost within the configured budget |
| `GET` | `/v1/runs/{run_id}` | Retrieve an execution record |

All management routes require the bearer token. JSON request bodies are limited to 1 MB. Agent responses recursively redact API keys, tokens, secrets, passwords, credentials, and authorization fields from configuration objects. Agent execution enforces the registered adapter, active state, explicit tool allowlist, and configured tool-round limit. Budget overruns return HTTP 409. The API is server-to-server; browser clients should call a trusted PanMedia backend rather than expose the token.

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

The completed .gitmodules inventory contains 1,532 pinned public repositories across all twenty requested organizations. Five separate skill submodules under skills/upstream are excluded from that count. Retrieve pinned source trees with git submodule update --init --recursive. The inventory records upstream source references; it does not establish that every source tree has been retrieved, reviewed, built, or integrated into the application. Each candidate project still requires relevance, license, dependency, compatibility, implementation, and test review.
