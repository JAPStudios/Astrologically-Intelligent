# Astrologically Intelligent

A native Android application and Python agent platform with model-provider routing, persistent conversations and memory, extensible tools and skills, multi-agent orchestration, goals, approvals, budgets, and execution records.

## Python agent platform

See [AGENT_RUNTIME.md](AGENT_RUNTIME.md) for setup, provider configuration, API usage, orchestration tools, plugin entry points, and security controls.

Run with Python 3.10+:

```sh
export ASTRO_AI_API_KEY="..."
export ASTRO_AI_MODEL="gpt-4.1-mini"
export ASTRO_AI_BASE_URL="https://api.openai.com/v1"
python -m astrologically_intelligent
```

The local service defaults to `127.0.0.1:8765`. It exposes `GET /health` and `POST /v1/chat`. Non-loopback binding requires a bearer token configured through `ASTRO_AI_API_TOKEN`.

## Android application

The native Android client is in `app/`. It provides a chat interface to the Python runtime. The emulator's default URL `http://10.0.2.2:8765` routes to a Python service running on the development host. Use HTTPS for remote deployments.

Build with Gradle 8.9, JDK 17, and Android SDK platform 35:

```sh
gradle assembleDebug
```

## Tests

```sh
python -m unittest discover -s tests -v
```

## Upstream integration

The target project is being expanded with source and working capabilities from the NousResearch, Omacom, OpenClaw, and PaperclipAI GitHub organizations. This is an ongoing repository-wide integration; an imported repository, source snapshot, compatibility layer, or feature is only counted as integrated after its code, dependencies, runtime behavior, and tests are actually incorporated.
