# Astrologically Intelligent — integrated agent platform

Astrologically Intelligent is the destination repository for the software and capabilities being integrated from the NousResearch, Omacom, OpenClaw, and PaperclipAI GitHub organizations. No product-purpose or platform category is excluded by the repository name.

## Existing runtime

The Python service provides multi-turn model conversations, OpenAI-compatible provider transport, tool calling, SQLite conversation history and memory, task records, Markdown skills, and a JSON HTTP API. The Android application is in `app/`.

Run the service with Python 3.10+:

```sh
export ASTRO_AI_API_KEY="..."
export ASTRO_AI_MODEL="gpt-4.1-mini"
export ASTRO_AI_BASE_URL="https://api.openai.com/v1"
python -m astrologically_intelligent
```

The service binds to loopback on port 8765 by default. It exposes `GET /health` and `POST /v1/chat`. Non-loopback binding requires `ASTRO_AI_API_TOKEN` with at least 24 characters; clients authenticate with a bearer token. Request bodies are limited to 1 MB.

## Implemented integration work

- **Agent organization and execution records:** SQLite-backed agent registration, adapter/model metadata, role and state, run lifecycle, and due-heartbeat discovery.
- **Goals:** hierarchical goal records with optional parent goal and owning agent.
- **Governance:** explicit approval requests with one-way pending-to-decision transitions.
- **Budgets:** per-agent or organization-level period budgets; cost recording is rejected when it would exceed the configured limit.
- **Plugin lifecycle:** discovery and loading of installed Python entry points in the `astrologically_intelligent.plugins` group. A plugin exposes `setup(registry)`. Plugins are executable trusted code and must be installed deliberately.
- **Existing capabilities:** provider abstraction, bounded tool-calling loop, persistent conversations and memory, work items, and Markdown skill discovery.

## Plugin entry-point example

In a Python package's `pyproject.toml`:

```toml
[project.entry-points."astrologically_intelligent.plugins"]
example = "example_plugin:plugin"
```

The referenced object must expose `setup(registry)`; it can register tools through `registry.register(name, description, parameters, handler)`.

## Integration status

This commit adds functioning orchestration primitives and plugin loading. It does not claim that every repository in the four organizations has been imported or that every upstream application has been fully ported. The source organizations contain many independent repositories and complete applications; repository-by-repository source ingestion, dependency integration, platform builds, and test execution remain necessary. No list of planned work is represented as completed functionality.

Run tests:

```sh
python -m unittest discover -s tests -v
```
