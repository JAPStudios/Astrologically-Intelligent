# Astrologically Intelligent

Astrologically Intelligent is a virtual intelligence and agent system for everyday work and research. Its core includes persistent conversations, memory, model routing, native tools, skills, multi-agent orchestration and a full-featured web interface.

## Runtime surfaces

The Python agent runtime can run headlessly with Python 3.10+. The full FastAPI system also mounts the runtime API in its own process; running the full web system does not require a second headless service.

```sh
python -m astrologically_intelligent
```

The headless service binds to `127.0.0.1:8765` by default. It exposes health, authenticated chat, session listing, safe conversation history and session deletion routes. Non-loopback binding requires a bearer token configured through `ASTRO_AI_API_TOKEN`.

The full web system lives in `astrologically_intelligent/`. Follow [its setup guide](astrologically_intelligent/README.md) and [runtime documentation](AGENT_RUNTIME.md). From that directory, start the web service with:

```sh
python -m uvicorn app:app --host 127.0.0.1 --port 7000
```

## JAPStudios service roles

- **CatChat** provides direct-message conversations. Its `astrologically-intelligent` assistant account sends each conversation through the full system's authenticated session and chat routes, preserving a separate continuing AI conversation for each CatChat thread.
- **Peanut Browsing** supplies first-party web research. The agent's `web_search` tool queries Peanut Browsing's indexed pages and `peanut_browsing_crawl` submits public sites to its crawler. Search does not silently switch to a competing search engine; results cover the sites present in Peanut Browsing's index.

## Upstream implementation map

Astrologically Intelligent incorporates working capabilities from the ten requested upstream organizations:

| Upstream | Implemented capability |
| --- | --- |
| [Anthropic](https://github.com/orgs/anthropics/repositories) | Native Messages API transport and tool-call conversion |
| [Herdr](https://github.com/orgs/herdrdev/repositories) | Guarded, read-only agent listing, status inspection and terminal-output tools |
| [n8n](https://github.com/orgs/n8n-io/repositories) | Workflow management operations |
| [NousResearch](https://github.com/orgs/NousResearch/repositories) | Hermes skill lifecycle patterns and NousResearch model discovery |
| [Odysseus](https://github.com/orgs/odysseus-dev/repositories) | Upstream codebase lineage and inherited runtime components |
| [OpenAI](https://github.com/orgs/openai/repositories) | Chat Completions and Responses transports with model-capability discovery |
| [OpenClaw](https://github.com/orgs/openclaw/repositories) | Read-only session inspection |
| [PaperclipAI](https://github.com/orgs/paperclipai/repositories) | Company and issue management operations |
| [Perplexity](https://github.com/orgs/perplexityai/repositories) | Provider transport |
| [xAI](https://github.com/orgs/xai-org/repositories) | Grok provider transport |

Upstream source is retained with its repository boundaries and license files. Native adapters, tools and skills are wired into the runtime where implemented; each upstream project remains independently versioned so updates can be reviewed without overwriting its licensing or security requirements.

## Tests

From the repository root:

```sh
python -m unittest discover -s tests -v
```

For the full web system, run `python -m pytest` from `astrologically_intelligent/`.
