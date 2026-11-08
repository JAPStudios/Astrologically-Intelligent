# Astrologically Intelligent

Astrologically Intelligent is an artificial neural network. CatChat is the direct-messaging service for private one-to-one and group conversations, persistent message history and read receipts; its reserved Astrologically Intelligent account can provide AI replies. WaveWeaver provides literary recommendations, Peanut Browsing provides research, PanMedia provides agent management, Terracotta provides artistic guidance, NoiseGround provides sound engineering assistance, MyOutlet provides video editing recommendations, Engzen provides programming review and correction and Honest Education provides fact-checking.

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

The completed .gitmodules inventory contains **1,532 pinned public repositories across all twenty requested organizations**. Organization-by-organization counts are recorded in [UPSTREAM_IMPORT.md](UPSTREAM_IMPORT.md). The six AI-query organizations are Apple, AWS, Brave, Google, Kagi Search, and Microsoft; the remaining fourteen use public-repository listings. Five separate skill submodules under skills/upstream are not included in the 1,532 repository count. These Git submodules preserve upstream source boundaries; they do not mean that the upstream applications or their functionality have been integrated into Astrologically Intelligent.

Retrieve the pinned source trees with:

```sh
git submodule update --init --recursive
```

The resumable importer in `scripts/import_upstream_orgs.py` can add later upstream repositories or refresh the inventory. It includes archived repositories and forks, skips URLs already represented as submodules, and pins each default-branch commit. It does not flatten or rewrite upstream source files.

## Upstream organizations

The requested upstream scope comprises public repositories from these GitHub organizations:

- [Anthropic](https://github.com/orgs/anthropics/repositories)
- [Apple](https://github.com/orgs/apple/repositories)
- [AWS](https://github.com/orgs/aws/repositories)
- [Brave](https://github.com/orgs/brave/repositories)
- [Cursor](https://github.com/orgs/cursor/repositories)
- [DeepSeek AI](https://github.com/orgs/deepseek-ai/repositories)
- [Google](https://github.com/orgs/google/repositories)
- [Herdr](https://github.com/orgs/herdrdev/repositories)
- [Kagi Search](https://github.com/orgs/kagisearch/repositories)
- [LukaLabs](https://github.com/orgs/lukalabs/repositories)
- [Meta Llama](https://github.com/orgs/meta-llama/repositories)
- [Microsoft](https://github.com/orgs/microsoft/repositories)
- [n8n](https://github.com/orgs/n8n-io/repositories)
- [NousResearch](https://github.com/orgs/NousResearch/repositories)
- [Odysseus](https://github.com/orgs/odysseus-dev/repositories)
- [OpenAI](https://github.com/orgs/openai/repositories)
- [OpenClaw](https://github.com/orgs/openclaw/repositories)
- [PaperclipAI](https://github.com/orgs/paperclipai/repositories)
- [Perplexity](https://github.com/orgs/perplexityai/repositories)
- [xAI](https://github.com/orgs/xai-org/repositories)

Apple, AWS, Brave, Google, Kagi Search, and Microsoft are queried for AI-related repositories; the other organizations use their public repository listings. These repositories are source references, not a claim that their projects or functionality have been incorporated into Astrologically Intelligent. Evaluate any proposed source use individually for licensing, compatibility, security, dependencies, executable behaviour, and tests.
