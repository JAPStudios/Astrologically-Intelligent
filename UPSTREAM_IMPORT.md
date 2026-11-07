# Upstream repository import

## Result

**Status: Source inventory imported — functionality integration and validation remain separate work.**

The current `.gitmodules` file contains **1,532 pinned public repositories across all twenty requested organizations**. The table below is counted directly from the committed Gitlink paths at the current inventory revision.

| Organization | Pinned submodules |
| --- | ---: |
| anthropics | 115 |
| apple | 4 |
| aws | 9 |
| brave | 3 |
| cursor | 10 |
| deepseek-ai | 46 |
| google | 50 |
| herdrdev | 5 |
| kagisearch | 2 |
| lukalabs | 20 |
| meta-llama | 12 |
| microsoft | 634 |
| n8n-io | 52 |
| NousResearch | 114 |
| odysseus-dev | 2 |
| openai | 277 |
| openclaw | 97 |
| paperclipai | 11 |
| perplexityai | 57 |
| xai-org | 12 |
| **Total** | **1,532** |

The inventory was counted directly from the current `.gitmodules` file. It records pinned Git submodules; it does not establish that every upstream source tree has been checked out, reviewed, built, or integrated into the application.

## Retrieving the source

The destination stores each upstream repository as a Git submodule pinned to a commit resolved from its default branch at import time. Retrieve the pinned source trees with:

```sh
git submodule update --init --recursive
```

Repositories using Git LFS may require Git LFS to be installed and their LFS objects fetched separately:

```sh
git submodule foreach --recursive 'git lfs pull'
```

Each submodule retains its upstream repository boundary, source layout, and license files. The submodules are not flattened into one directory or relicensed by the destination repository.

## Import tooling

`scripts/import_upstream_orgs.py` lists public repositories for the configured organizations, resolves default-branch commits, and records Gitlinks and `.gitmodules` entries. It is resumable and skips existing submodule URLs. Six broad organizations use a repository search for `AI` rather than importing every public repository. GitHub limits each repository-search query to 1,000 results; the importer reports when an organization reaches that limit instead of failing on page eleven. The `Import Upstream Repositories` workflow performs imports in bounded batches.

## Runtime integrations

The application also contains API integrations for n8n workflow management, Paperclip company/issue operations, Perplexity Search, and read-only OpenClaw session access, plus native Anthropic Messages API transport and provider routing for xAI and Perplexity. These are specific application integrations; they do not mean the upstream applications themselves have all been merged into one runtime.

## Remaining work

The source inventory is not the completion criterion for the software. Each upstream project still needs an evidence-based disposition: relevant functionality identified, license and dependency obligations reviewed, compatibility assessed, any selected functionality integrated into the application, and automated tests added. Projects that are irrelevant, incompatible, redundant, or unsafe to incorporate should be documented as such rather than copied indiscriminately. The complete application also requires repeatable dependency installation, test execution, security checks, and deployment validation.
