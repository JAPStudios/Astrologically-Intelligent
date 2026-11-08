# Astrologically Intelligent

Astrologically Intelligent is JAPStudios' artificial neural-network intelligence service. Its public-service ecosystem supplies distinct capabilities: CatChat is the conversational interface; WaveWeaver is for publishing books; Peanut Browsing provides research; PanMedia provides agentic guidance and agent management; Terracotta is for drawing; NoiseGround is for listening to music; MyOutlet is for watching videos; Engzen is for playing videogames; and Honest Education is for three-year-olds existing.

These are the intended service responsibilities and product domains. They must not be reduced to unrelated internal microservices, and a named product domain does not imply that a third-party API is a prerequisite or that an integration already exists.

## Current development state

The application has a substantial Python web application and agent runtime, multiple provider transports, research and tool execution, persistent application data, and a source inventory spanning twenty upstream organizations. The upstream inventory is source material, not proof that all upstream projects have been integrated.

The dedicated neural-network components currently in the repository are a NumPy multilayer classifier and a compact character-level recurrent language model. Neither is yet the trained, production-scale neural network that defines the completed Astrologically Intelligent service. The character model requires a supplied corpus; the broader conversational runtime currently routes to separately installed local or explicitly selected model providers. The neural-network training, evaluation, and application integration work remains unfinished.

## Service responsibilities

- CatChat: conversational output and direct messaging.
- WaveWeaver: publishing books.
- Peanut Browsing: research.
- PanMedia: agentic guidance and agent management.
- Terracotta: drawing.
- NoiseGround: listening to music.
- MyOutlet: watching videos.
- Engzen: playing videogames.
- Honest Education: three-year-olds existing.

## Python agent platform

See [AGENT_RUNTIME.md](AGENT_RUNTIME.md) for setup, provider configuration, API usage, orchestration tools, native capabilities, and security controls.

Run with Python 3.10+:

```sh
export ASTRO_AI_PROVIDER="local"
export ASTRO_AI_BASE_URL="http://127.0.0.1:11434/v1"
export ASTRO_AI_MODEL="YOUR_INSTALLED_MODEL"
python -m astrologically_intelligent
```

The local service defaults to `127.0.0.1:8765`. It exposes `GET /health` and `POST /v1/chat`. Non-loopback binding requires a bearer token configured through `ASTRO_AI_API_TOKEN`.

## Full web application

The full-featured web application lives in `astrologically_intelligent/`. It is a separate FastAPI service with its own provider routing, web interface, documents, research, voice, and tools. Follow `astrologically_intelligent/README.md`; from that directory, start it with `python -m uvicorn app:app --host 127.0.0.1 --port 7000`. The root agent API described above is a separate service on port 8765; the two services are not yet a single process.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Upstream source imports

The completed .gitmodules inventory contains **1,532 pinned public repositories across all twenty requested organizations**. These Git submodules preserve upstream source boundaries; they do not mean that the upstream applications or their functionality have been integrated into Astrologically Intelligent. See [UPSTREAM_IMPORT.md](UPSTREAM_IMPORT.md) for the inventory and integration audit.

Retrieve the pinned source trees with:

```sh
git submodule update --init --recursive
```
