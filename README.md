# Astrologically Intelligent

Astrologically Intelligent is a virtual intelligence and agent system for everyday work and research. Its core includes persistent conversations, memory, model routing, native tools, skills, multi-agent orchestration and a full-featured web interface.

## Runtime surfaces

The Python agent runtime can run headlessly with Python 3.10+. The full FastAPI system mounts the runtime API in the same process as its web interface; running the full web system does not require a second headless service.

The optional headless service binds to `127.0.0.1:8765` by default and requires provider-specific environment settings. It exposes health, authenticated chat, session listing, safe conversation history and session deletion routes. Non-loopback binding requires a bearer token configured through `ASTRO_AI_API_TOKEN`.

CatChat direct messages use the full web system's `/api/session` and `/api/chat` routes. The optional `/v1/chat` route is the headless agent API used by standalone clients. The full web system lives in `astrologically_intelligent/`. Follow [its setup guide](astrologically_intelligent/README.md) and [runtime documentation](AGENT_RUNTIME.md). From that directory, start the web service with:

```sh
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

## JAPStudios service roles

- **CatChat** provides direct-message conversations. Its `astrologically-intelligent` assistant account sends each conversation through the full system's authenticated session and chat routes, preserving a separate continuing AI conversation for each CatChat thread.
- **Peanut Browsing** supplies the first-party research engine. The agent's `web_search` tool queries Peanut Browsing's indexed pages and `peanut_browsing_crawl` submits public sites to its crawler when `PEANUT_SEARCH_API_URL` and `PEANUT_SEARCH_API_KEY` are configured. Production search still requires the gateway to be deployed over HTTPS and the index to contain submitted websites.

## Upstream implementation map

Astrologically Intelligent incorporates working capabilities from the ten requested upstream organizations:

| Upstream | Implemented capability |
| --- | --- |
| [Anthropic](https://github.com/orgs/anthropics/repositories) | Native Messages API transport and tool-call conversion |
| [Herdr](https://github.com/orgs/herdrdev/repositories) | Guarded, read-only agent listing, status inspection and terminal-output tools |
| [n8n](https://github.com/orgs/n8n-io/repositories) | Upstream n8n skill source; native workflow API tools remain to be implemented |
| [NousResearch](https://github.com/orgs/NousResearch/repositories) | Hermes skill lifecycle patterns and NousResearch model discovery |
| [Odysseus](https://github.com/orgs/odysseus-dev/repositories) | Upstream codebase lineage and inherited runtime components |
| [OpenAI](https://github.com/orgs/openai/repositories) | Chat Completions and Responses transports with model-capability discovery |
| [OpenClaw](https://github.com/orgs/openclaw/repositories) | Agent-skill source and legacy session-migration support; live Gateway tool calls remain to be implemented |
| [PaperclipAI](https://github.com/orgs/paperclipai/repositories) | Upstream source retained for native company and issue functionality; its API adapter remains to be implemented |
| [Perplexity](https://github.com/orgs/perplexityai/repositories) | Provider transport; Peanut Browsing remains the first-party search engine |
| [xAI](https://github.com/orgs/xai-org/repositories) | Grok provider transport |

Upstream source is retained with its repository boundaries and license files. Native adapters, tools and skills are wired into the runtime where implemented; each upstream project remains independently versioned so updates can be reviewed without overwriting its licensing or security requirements.

## Android client

The Android client is a supplementary interface to the same authenticated agent API. It is not a separate intelligence engine. Build and run its unit tests from `app/` with `gradle testDebugUnitTest assembleDebug`.

## Tests

From the repository root:

```sh
python -m unittest discover -s tests -v
```

For the full web system, run `python -m pytest` from `astrologically_intelligent/`.
