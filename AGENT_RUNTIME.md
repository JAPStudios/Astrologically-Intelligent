# Astrologically Intelligent — agent runtime

This repository now contains a native Python agent runtime designed around the existing astrology application. It adopts compatible architectural ideas from NousResearch Hermes (provider abstraction, tool registry, durable sessions and memory), OpenClaw (a local service/API entry point and extensible tool surface), and Paperclip (durable work items and explicit task states). Omarchy's Linux desktop configuration is not a suitable runtime dependency for this Android/Python application; its reusable UI ideas remain a separate native Android integration task.

## Run

Python 3.10+; no third-party Python packages are required.

```sh
export ASTRO_AI_API_KEY="..."
export ASTRO_AI_MODEL="gpt-4.1-mini"
export ASTRO_AI_BASE_URL="https://api.openai.com/v1"
python -m astrologically_intelligent
```

The HTTP service binds to `127.0.0.1:8765` by default:
- `GET /health`
- `POST /v1/chat` with JSON `{"message":"...","session_id":"optional-stable-id"}`

For Gemini's OpenAI-compatible endpoint, configure `ASTRO_AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `ASTRO_AI_MODEL`, and an API key. Ollama can be used with `ASTRO_AI_BASE_URL=http://127.0.0.1:11434/v1`; local endpoints may omit the API key. Other compatible providers can be configured by base URL and model.

For a non-loopback bind, set `ASTRO_AI_API_TOKEN` to a random value of at least 24 characters. Clients must send `Authorization: Bearer <token>`. The server refuses an externally reachable bind without this token.

## Included functionality

- OpenAI-compatible provider transport with configurable model, endpoint, API key, timeout, and HTTP error reporting.
- Multi-turn tool-calling loop with a bounded number of rounds.
- SQLite persistence for conversations, namespaced memories, and work items.
- Built-in tools for explicit memory save/recall and work-item create/list/update.
- Local JSON HTTP API with request-size limits, constant-time bearer-token comparison, no-store responses, and loopback-only default.
- Unit tests and a dedicated GitHub Actions workflow.

## Scope and integration status

This is an implemented Python runtime, not a wholesale copy of Hermes, OpenClaw, Paperclip, or Omarchy. The upstream projects are large, independent applications with different execution environments. Their source trees are not interchangeable with this Android/Python codebase. This integration ports compatible subsystem designs and leaves platform-specific components out rather than importing inert scripts or presenting configuration as functioning software.

Not yet implemented: Android UI wiring, background scheduling, messaging-channel adapters, browser automation, MCP transport, model-provider-specific OAuth flows, multi-agent isolation, budget enforcement, and astronomical ephemeris/chart computation. No astrology chart result is fabricated by this runtime.
