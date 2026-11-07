# Upstream repository import

## Result

**Status: Source inventory imported — functionality integration and validation remain separate work.**

The current `.gitmodules` file contains **742 pinned public repositories across the original ten organizations**. The requested source scope is twenty organizations. The importer is being expanded to include the remaining ten: `cursor`, `deepseek-ai`, `lukalabs`, and `meta-llama` are imported by public-repository listing; `apple`, `aws`, `brave`, `google`, `kagisearch`, and `microsoft` are searched for repositories matching GitHub’s `org:<name> AI` query. These additional repositories are not counted in the current 742 until the import workflow records their Gitlinks. Five repositories from `herdrdev` were added in the latest Herdr import batch. The current organization-directory counts are:

| Organization | Pinned submodules |
| --- | ---: |
| anthropics | 115 |
| herdrdev | 5 |
| n8n-io | 52 |
| NousResearch | 114 |
| odysseus-dev | 2 |
| openai | 277 |
| openclaw | 97 |
| paperclipai | 11 |
| perplexityai | 57 |
| xai-org | 12 |
| **Total** | **742** |

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
