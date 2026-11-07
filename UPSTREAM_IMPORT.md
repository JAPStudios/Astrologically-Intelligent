# Upstream repository import

## Result

**Status: complete — source inventory imported; functionality integration remains a separate engineering task.**

The completed .gitmodules inventory contains **1,532 pinned public repositories across all twenty requested organizations**. The counts below are calculated directly from the current upstream organization submodule paths.

| Organization | Pinned repositories |
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

Five additional skill submodules under skills/upstream are maintained separately. They are not included in the total above.

The six AI-query organizations are apple, aws, brave, google, kagisearch, and microsoft. The remaining fourteen organizations use public-repository listings. The importer completed its bounded GitHub Actions batches successfully. The inventory includes archived repositories and forks where returned by the listing or query. Existing submodule URLs are skipped; each imported repository is pinned to the commit resolved from its default branch.

The inventory records Git submodules. It does not establish that every upstream source tree has been checked out, reviewed, built, or integrated into the application.

## Retrieving the source

The destination stores each upstream repository as a Git submodule pinned to a commit resolved from its default branch at import time. Retrieve the pinned source trees with:

~~~
git submodule update --init --recursive
~~~

Repositories using Git LFS may require Git LFS to be installed. Fetch their LFS objects separately:

~~~
git submodule foreach --recursive 'git lfs pull'
~~~

Each submodule retains its upstream repository boundary, source layout, and license files. The submodules are not flattened into one directory or relicensed by the destination repository.

## Import tooling

scripts/import_upstream_orgs.py lists public repositories for the configured organizations, resolves default-branch commits, and records Gitlinks plus .gitmodules entries. It is resumable and skips existing submodule URLs. Six broad organizations use a repository search for AI rather than importing every public repository. GitHub limits each repository-search query to 1,000 results; the completed Microsoft query returned 634 pinned repositories, below that limit. The Import Upstream Repositories workflow performs imports in bounded batches.

## Runtime integrations

The application contains specific API integrations for n8n workflow management, Paperclip company and issue operations, Perplexity Search, read-only OpenClaw session access, Anthropic Messages API transport, plus provider routing for xAI, Perplexity, and DeepSeek. These are selected application integrations; they do not mean the upstream applications themselves have all been merged into one runtime. The CatChat integration plus Peanut Browsing search tools are documented in AGENT_RUNTIME.md.

## Remaining work

The source inventory is not the completion criterion for the software. Each upstream project still needs an evidence-based disposition: identify relevant functionality, review license and dependency obligations, assess compatibility and security, integrate selected functionality, then add automated tests. Projects that are irrelevant, incompatible, redundant, or unsafe to incorporate should be documented as such rather than copied indiscriminately. The complete application also requires repeatable dependency installation, test execution, security checks, and deployment validation.
