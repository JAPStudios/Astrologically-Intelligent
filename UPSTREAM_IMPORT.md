# Upstream implementation map

Astrologically Intelligent uses upstream work through runtime adapters, native tools, skills, model discovery and inherited codebase components. The organization list is a development scope, not a repository-count metric.

| Upstream organization | Functionality in the system |
| --- | --- |
| [Anthropic](https://github.com/orgs/anthropics/repositories) | Native Messages API transport, tool-use blocks and tool-result conversion |
| [Herdr](https://github.com/orgs/herdrdev/repositories) | Guarded read-only agent listing, status inspection and terminal-output tools |
| [n8n](https://github.com/orgs/n8n-io/repositories) | Upstream n8n skill source; native workflow API tools remain to be implemented |
| [NousResearch](https://github.com/orgs/NousResearch/repositories) | Hermes progressive skill-disclosure patterns and NousResearch model discovery |
| [Odysseus](https://github.com/orgs/odysseus-dev/repositories) | Upstream codebase lineage and inherited runtime components |
| [OpenAI](https://github.com/orgs/openai/repositories) | Chat Completions and Responses transports plus model-capability discovery |
| [OpenClaw](https://github.com/orgs/openclaw/repositories) | Agent-skill source and legacy session-migration support; live Gateway tool calls remain to be implemented |
| [PaperclipAI](https://github.com/orgs/paperclipai/repositories) | Upstream source retained for native company and issue functionality; its API adapter remains to be implemented |
| [Perplexity](https://github.com/orgs/perplexityai/repositories) | Provider transport; Peanut Browsing remains the first-party search engine |
| [xAI](https://github.com/orgs/xai-org/repositories) | Grok provider transport |

## JAPStudios service roles

- CatChat is the direct-message surface. Its assistant account uses the full Astrologically Intelligent session and chat routes, maintaining a continuing AI session for each direct-message conversation.
- Peanut Browsing is the first-party research engine. The agent's search tool queries its index and its crawl tool submits public sites to its crawler.
- PanMedia is intended to manage agents. The current PanMedia repository does not yet publish a usable API or implementation contract for an in-process adapter.
- Engzen is intended to provide programming capabilities. The current Engzen repository identifies its contents as a MyOutlet extension rather than documenting a programming API.
- Honest Education is intended to provide verified information and fact-checking. A corresponding public repository or API contract has not yet been located in the connected GitHub account.

## Source boundaries

Upstream repositories retain their own source layout, license files and version history. A submodule reference alone is not treated as a completed integration: runtime functionality is provided by the adapters, tools and skills listed above. Changes to upstream code are reviewed for license obligations, dependency compatibility, security and tests before they are incorporated.

## Import tooling

`scripts/import_upstream_orgs.py` maintains the upstream source references for the ten configured organizations. It resolves default-branch commits and records Gitlinks and `.gitmodules` entries. The `Import Upstream Repositories` workflow performs imports in bounded batches.

## Validation

Provider adapters, native tools, skills and service interfaces require automated tests. Full completion also requires repeatable dependency installation, test execution, security checks and deployment validation.
