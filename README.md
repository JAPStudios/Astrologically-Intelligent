# Astrologically Intelligent

Astrologically Intelligent is an extensible AI application and agent platform with persistent conversations and memory, model-provider routing, tools, skills, multi-agent orchestration, and native Android access.

## Python agent platform

See [AGENT_RUNTIME.md](AGENT_RUNTIME.md) for setup, provider configuration, API usage, orchestration tools, plugin entry points, external integrations, and security controls.

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

## Upstream organizations

The requested upstream scope comprises public repositories from these GitHub organizations:

- [Anthropic](https://github.com/orgs/anthropics/repositories)
- [n8n](https://github.com/orgs/n8n-io/repositories)
- [NousResearch](https://github.com/orgs/NousResearch/repositories)
- [Odysseus](https://github.com/orgs/odysseus-dev/repositories)
- [OpenAI](https://github.com/orgs/openai/repositories)
- [OpenClaw](https://github.com/orgs/openclaw/repositories)
- [PaperclipAI](https://github.com/orgs/paperclipai/repositories)
- [Perplexity](https://github.com/orgs/perplexityai/repositories)
- [xAI](https://github.com/orgs/xai-org/repositories)

This is a repository-wide integration effort. Provider compatibility, an API connector, a source reference, or a catalogue is not equivalent to importing an upstream repository's source and functionality. Track each upstream project against its actual imported code, required dependencies, executable behavior, and tests.
