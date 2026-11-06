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

## n8n workflow integration

Astrologically Intelligent can call an existing n8n instance through its public REST API. Configure:

```sh
export N8N_BASE_URL="https://n8n.example.com"
export N8N_API_KEY="..."
```

Available tools:

- `n8n.workflows.list`: list workflows, with bounded pagination.
- `n8n.workflows.get`: retrieve one workflow by ID.
- `n8n.workflows.activate`: activate a workflow.
- `n8n.workflows.deactivate`: deactivate a workflow.
- `n8n.executions.list`: retrieve execution history with workflow or project filters, status filters, time bounds, cursor pagination and optional execution data.
- `n8n.executions.get`: retrieve one execution; detailed execution data is opt-in.

The connector uses the n8n API-key header. HTTPS is required except for localhost. It does not claim to vendor the n8n application or its node catalogue.

## Paperclip agent-organization integration

Configure an authenticated Paperclip agent API token and instance URL:

```sh
export PAPERCLIP_BASE_URL="https://paperclip.example.com"
export PAPERCLIP_API_KEY="..."
```

The connector follows Paperclip's documented company-scoped API routes and uses bearer-token authentication. Available tools:

- `paperclip.agents.list`: list agents in a company.
- `paperclip.issues.list`: list company issues with optional status, assignee, and project filters.
- `paperclip.issues.create`: create a company issue.
- `paperclip.goals.create`: create a company goal.
- `paperclip.approvals.list`: list company approval requests.

The token's own Paperclip permissions and company membership remain authoritative. This connector does not install or vendor the Paperclip server, UI, database, or adapter packages.

## OpenClaw Gateway integration

Configure the private Gateway URL and bearer token:

```sh
export OPENCLAW_GATEWAY_URL="http://127.0.0.1:18789"
export OPENCLAW_GATEWAY_TOKEN="..."
```

The integration exposes `openclaw.sessions.list`, `openclaw.sessions.search` and `openclaw.sessions.history` through the Gateway's authenticated `POST /tools/invoke` endpoint. These operations are read-only. Search results include message context identifiers that can be passed to history retrieval. The client deliberately allowlists these three tools rather than exposing arbitrary invocation: the Gateway token can grant powerful operator access. Keep the Gateway on loopback or a private network.

## HTTP service

The service binds to `127.0.0.1:8765` by default. It exposes `GET /health`, authenticated `GET /v1/history?session_id=...`, `GET /v1/sessions`, authenticated `DELETE /v1/sessions/{session_id}` and `POST /v1/chat`. Conversation deletion removes only messages belonging to the selected session and returns 404 when that session has no messages. Conversation history returns up to 200 messages (40 by default) in chronological order. Non-loopback binding requires `ASTRO_AI_API_TOKEN` with at least 24 characters; clients authenticate with a bearer token. Request bodies are limited to 1 MB.

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
- n8n: `n8n.workflows.list`, `n8n.workflows.get`, `n8n.workflows.activate`, `n8n.workflows.deactivate`
- Paperclip: `paperclip.agents.list`, `paperclip.issues.list`, `paperclip.issues.create`, `paperclip.goals.create`, `paperclip.approvals.list`
- Perplexity: `perplexity.search`
- OpenClaw: `openclaw.sessions.list` (read-only)

## Plugins

Installed Python distributions may register entry points under `astrologically_intelligent.plugins`. Each entry point must load an object exposing `setup(registry)`. Plugins are executable trusted code; install only reviewed packages.

## Tests

```sh
python -m unittest discover -s tests -v
```

The committed public-repository inventory currently contains 741 non-empty repositories from nine of the ten requested organizations. The earlier import skipped three empty repositories: `anthropics/homebrew-claude`, `NousResearch/forge-feedback`, and `perplexityai/pplx-rs`. The `herdrdev` organization was omitted from that inventory and remains outstanding. The importer is now configured to include it; its repositories still need to be inventoried, pinned, retrieved, reviewed, and committed. Run `git submodule update --init --recursive` to retrieve source trees already represented by Gitlinks. Source inclusion does not mean every upstream application has been merged into the runtime or that all upstream projects share one execution model.
