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

## JAPStudios public-service integration audit

This section records the current repository evidence for the service relationships described by JAPStudios. A source repository, a documented endpoint contract, and a tested integration are distinct states; no missing service endpoint is inferred or fabricated.

| JAPStudios public service | Current evidence in the accessible repositories | Astrologically Intelligent integration status |
| --- | --- | --- |
| CatChat — conversational output | `JAPStudios/CatChat` contains a working messaging service and documents its assistant-account path to Astrologically Intelligent through `POST /api/session` and `POST /api/chat`. Its tests use a mocked responder. | Integration contract documented. Live service-to-service deployment has not been verified. |
| Peanut Browsing — research | `JAPStudios/Peanut-Browsing` contains the first-party crawler, index, and authenticated search gateway. The full web application has native search and crawl tools; the Deep Research provider connection was merged in PR #16. | Implemented and covered by deterministic tool-cycle and navigator tests. Live production-index coverage has not been verified. |
| PanMedia — agentic guidance | `JAPStudios/PanMedia` uses the authenticated agent, goal, approval, budget, and run APIs in this repository. Cross-repository backend/proxy tests were reported passing in the completion issue. | Backend API and service proxy implemented. Live public deployment has not been verified. |
| WaveWeaver — literary recommendations | `JAPStudios/WaveWeaver` exists, but its current repository is a Wix site scaffold with astrology/lifestyle page files; no literary-recommendation API or recommendation implementation was identified. | Not integrated; service capability/API contract remains unverified. |
| Terracotta — artistic guidance | No matching repository was present in the accessible JAPStudios repository listing, and no service API contract was identified in this repository. | Not integrated; implementation source/API contract is required. |
| NoiseGround — sound engineering assistance | No matching repository was present in the accessible JAPStudios repository listing, and no service API contract was identified in this repository. | Not integrated; implementation source/API contract is required. |
| MyOutlet — video editing recommendations | `JAPStudios/MyOutlet` contains an audiovisual publishing and streaming platform, including creator channels, uploads, live streams, and moderation. No video-editing recommendation API was identified. | Not integrated for the stated video-editing capability; the existing media platform is not counted as that feature. |
| Engzen — programming review and correction | The accessible `JAPStudios/Engzen` repository currently identifies itself as `MyOutlet-Extension` and contains browser-extension files plus funding documents. No programming-review or code-correction API was identified. | Not integrated for the stated programming capability. |
| Honest Education — fact checking | No matching repository was present in the accessible JAPStudios repository listing, and no service API contract was identified in this repository. | Not integrated; implementation source/API contract is required. |

These gaps do not change the service responsibilities defined by JAPStudios. They identify work that cannot be completed safely by guessing endpoints or treating unrelated repository contents as the required service. Update this table only when the relevant implementation and its integration tests provide evidence.

## Destination-repository licensing status

The destination repository currently has no top-level license file and GitHub reports no detected repository license. The 1,532 imported Git submodules retain their own upstream repository boundaries and license files; that does not license the destination repository's original code or grant blanket permission to redistribute the submodule contents. Do not infer a project-wide license from the upstream inventory. A project-wide license decision and a source-by-source redistribution review remain release blockers.
