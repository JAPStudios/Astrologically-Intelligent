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
| `xai` / `grok` | OpenAI-compatible Chat Completions transport | Configure the xAI API endpoint and key |
| `perplexity` | OpenAI-compatible transport only | Requires a Perplexity endpoint/model supporting the Chat Completions tool schema |
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

## Plugins

Installed Python distributions may register entry points under `astrologically_intelligent.plugins`. Each entry point must load an object exposing `setup(registry)`. Plugins are executable trusted code; install only reviewed packages.

## Tests

```sh
python -m unittest discover -s tests -v
```

The organization-wide upstream import remains in progress. No source tree is counted as imported merely because an API connector or compatibility layer exists.
