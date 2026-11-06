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

## Full web application

The full-featured web application lives in `astrologically_intelligent/`. It is a separate FastAPI service with its own provider routing, web interface, documents, research, voice, tools, and integrations. Follow `astrologically_intelligent/README.md`; from that directory, start it with `python -m uvicorn app:app --host 127.0.0.1 --port 7000`. The root agent API described above is a separate service on port 8765; the two services are not yet a single process.

## Android application

The native Android client is in `app/`. It connects to the root Python agent API (`/v1/chat`) and restores its latest 40 messages from the authenticated `/v1/history` endpoint when a session opens. It defaults to `http://10.0.2.2:8765` for an Android emulator reaching the development host. It does not yet expose every feature in the full web application. Use HTTPS plus a configured bearer token for remote deployments.

Build with Gradle 8.9, JDK 17, and Android SDK platform 35:

```sh
gradle assembleDebug
```

## Tests

```sh
python -m unittest discover -s tests -v
```

## Upstream source imports

The committed upstream inventory currently covers **nine of the ten requested organizations**, with 741 pinned Git submodules. The previous inventory contained 744 public repositories; three empty repositories had no commit or source tree and were skipped. The `herdrdev` organization was omitted from that import and remains outstanding. The importer is now configured for all ten organizations, but the additional Herdr repositories still need to be inventoried, pinned, retrieved, reviewed, and committed.

Initialize and retrieve every imported source tree with:

```sh
git submodule update --init --recursive
```

The resumable importer in `scripts/import_upstream_orgs.py` can add later upstream repositories or refresh the inventory. It includes archived repositories and forks and skips URLs already represented as submodules. It pins each default-branch commit; it does not flatten or rewrite upstream source files.

## Upstream organizations

The requested upstream scope comprises public repositories from these GitHub organizations:

- [Anthropic](https://github.com/orgs/anthropics/repositories)
- [Herdr](https://github.com/orgs/herdrdev/repositories)
- [n8n](https://github.com/orgs/n8n-io/repositories)
- [NousResearch](https://github.com/orgs/NousResearch/repositories)
- [Odysseus](https://github.com/orgs/odysseus-dev/repositories)
- [OpenAI](https://github.com/orgs/openai/repositories)
- [OpenClaw](https://github.com/orgs/openclaw/repositories)
- [PaperclipAI](https://github.com/orgs/paperclipai/repositories)
- [Perplexity](https://github.com/orgs/perplexityai/repositories)
- [xAI](https://github.com/orgs/xai-org/repositories)

This is a repository-wide integration effort. Provider compatibility, an API connector, a source reference, or a catalogue is not equivalent to importing an upstream repository's source and functionality. Track each upstream project against its actual imported code, required dependencies, executable behavior, and tests.
