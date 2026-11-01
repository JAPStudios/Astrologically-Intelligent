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

Anthropic transport maps system messages, assistant tool-use blocks, tool schemas, and tool results to the runtime's function-tool interface. xAI and Perplexity are not represented as native vendor SDK integrations here.

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

The integration currently exposes only `openclaw.sessions.list`, through the documented `POST /tools/invoke` endpoint and the `sessions_list` read-only tool. It deliberately does not expose arbitrary tool invocation: OpenClaw documents the bearer token as full operator access, and the endpoint can execute powerful host actions depending on policy. Keep the Gateway on loopback or a private network.

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

The full public-repository import is complete: 740 non-empty repositories from all nine requested organizations are pinned as Git submodules. The three empty repositories skipped were `anthropics/homebrew-claude`, `NousResearch/forge-feedback`, and `perplexityai/pplx-rs`. Run `git submodule update --init --recursive` to retrieve the source trees. The import is source inclusion; it does not claim that every upstream application has been merged into the runtime or that all upstream projects share one execution model.
