# Astrologically Intelligent

Astrologically Intelligent is an AI application and agent platform for everyday work and research, with persistent conversations and memory, model-provider routing, native tools and skills, and multi-agent orchestration.

## Python agent platform

See [AGENT_RUNTIME.md](AGENT_RUNTIME.md) for setup, provider configuration, API usage, orchestration tools, native capabilities, and security controls.

Run with Python 3.10+:

```sh
# Start Ollama locally and install a model before launching the runtime.
# Set ASTRO_AI_MODEL to the exact identifier shown by: ollama list
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

The current `.gitmodules` inventory contains **742 pinned public repositories across all ten requested GitHub organizations**, including five repositories from `herdrdev`. Three previously listed repositories were empty and had no source tree to pin. The inventory records upstream repositories as Git submodules; it does not claim that their applications or functionality have been merged into Astrologically Intelligent.

Retrieve the pinned source trees with:

```sh
git submodule update --init --recursive
```

The resumable importer in `scripts/import_upstream_orgs.py` can add later upstream repositories or refresh the inventory. It includes archived repositories and forks, skips URLs already represented as submodules, and pins each default-branch commit. It does not flatten or rewrite upstream source files.

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

These repositories are source references, not a claim that their projects or functionality have been incorporated into Astrologically Intelligent. Evaluate any proposed source use individually for licensing, compatibility, security, dependencies, executable behaviour, and tests.
