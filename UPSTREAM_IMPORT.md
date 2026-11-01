# Upstream repository import

## Result

**Status: Complete**

- Public repositories discovered across the nine requested GitHub organizations: **743**
- Non-empty repositories pinned in the destination: **740**
- Empty repositories skipped because they had no commit/source tree: **3**
- Gitlinks in the destination tree: **740**
- Entries in `.gitmodules`: **740**
- Import workflow: `Import Upstream Repositories`
- Successful import run: [41318801539](https://github.com/JAPStudios/Astrologically-Intelligent/actions/runs/41318801539)
- Final import batch commit: [b83cb83](https://github.com/JAPStudios/Astrologically-Intelligent/commit/b83cb83e682aa724a5794b2a8dfb723e0a073721)

## Imported repositories by organization

| Organization | Imported submodules |
| --- | ---: |
| anthropics | 115 |
| n8n-io | 53 |
| NousResearch | 115 |
| odysseus-dev | 2 |
| openai | 278 |
| openclaw | 98 |
| paperclipai | 11 |
| perplexityai | 56 |
| xai-org | 12 |
| **Total** | **740** |

Five skill-oriented repositories are located under `skills/upstream/` so the runtime's recursive skill loader can discover their `SKILL.md` files. The remaining repositories are under `upstream/<organization>/<repository>`.

## Empty repositories skipped

These three public repository records had no importable commit:

- `anthropics/homebrew-claude`
- `NousResearch/forge-feedback`
- `perplexityai/pplx-rs`

## Retrieving the source

The destination stores each upstream repository as a Git submodule pinned to the commit resolved from its default branch at import time. The upstream source trees are retrieved with:

```sh
git submodule update --init --recursive
```

Repositories using Git LFS may require Git LFS to be installed and their LFS objects fetched separately:

```sh
git submodule foreach --recursive 'git lfs pull'
```

Each submodule retains its upstream repository boundary, source layout, and license files. The submodules are not flattened into one directory or relicensed by the destination repository.

## Import tooling

`scripts/import_upstream_orgs.py` lists all public repositories for the nine configured organizations, resolves each default-branch commit, and records its Gitlink and `.gitmodules` entry. It is resumable and skips existing submodule URLs. The `Import Upstream Repositories` workflow performs the import in bounded batches.

## Runtime integrations

The destination also contains working API integrations for n8n workflow management, Paperclip company/issue operations, Perplexity Search, and read-only OpenClaw session listing, plus native Anthropic Messages API transport and provider routing for xAI and Perplexity. These connectors complement the imported source; they do not imply that every upstream application is already merged into one runtime.
