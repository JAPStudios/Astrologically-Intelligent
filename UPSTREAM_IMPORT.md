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

## Existing optional external-provider and connector code

The repository currently contains optional connector/provider code paths for n8n workflow management, Paperclip operations, OpenClaw session access, Anthropic Messages transport, Perplexity Search, and xAI/Perplexity/DeepSeek model routing. This is an inventory of existing code, not a recommendation to integrate competitors, not a statement of partnership or endorsement, and not a requirement for Astrologically Intelligent's core capabilities. These adapters must not be treated as the product's differentiator or as substitutes for JAPStudios' own intelligence and services. No additional competitor integration should be introduced as a development objective. The CatChat and Peanut Browsing service relationships are documented separately in AGENT_RUNTIME.md.

## Remaining work

The source inventory is not the completion criterion for the software. Each upstream project still needs an evidence-based disposition: identify relevant functionality, review license and dependency obligations, assess compatibility and security, integrate selected functionality, then add automated tests. Projects that are irrelevant, incompatible, redundant, or unsafe to incorporate should be documented as such rather than copied indiscriminately. The complete application also requires repeatable dependency installation, test execution, security checks, and deployment validation.

## JAPStudios public-service responsibilities and evidence

The following are JAPStudios' own service names and product responsibilities. They are not aliases for, equivalents of, or dependencies on unrelated third-party products. A Wix CMS inspection, missing endpoint, or absent content collection cannot establish that a capability is absent from Astrologically Intelligent's own application. Likewise, the presence of general-purpose tools does not by itself prove that a specialist workflow is complete.

| JAPStudios public service | Defined responsibility | Evidence status in this document |
| --- | --- | --- |
| CatChat | Conversational output | A service API contract is documented; live deployment is not verified here. |
| Peanut Browsing | Research | First-party search/crawl tools are present; live production-index coverage is not verified here. |
| PanMedia | Agentic guidance and agent management | Backend API and service proxy implementation are documented; live public deployment is not verified here. |
| WaveWeaver | Literary recommendations | No conclusion about native application capability is drawn from Wix CMS metadata. |
| Terracotta | Artistic guidance | No conclusion about native application capability is drawn from Wix CMS metadata. |
| NoiseGround | Sound-engineering assistance | No conclusion about native application capability is drawn from Wix CMS metadata. |
| MyOutlet | Video-editing recommendations | No conclusion about native application capability is drawn from Wix CMS metadata. |
| Engzen | Programming review and correction | No conclusion about native application capability is drawn from Wix CMS metadata. |
| Honest Education | Fact-checking | No conclusion about native application capability is drawn from Wix CMS metadata. |

The service responsibilities are the product requirements. Implementations must be assessed in the application itself against those requirements; a separate service API is not a prerequisite. Wix CMS and site-setting observations below concern only those sites' exposed CMS data and cannot be used as evidence that the corresponding Astrologically Intelligent capability does or does not exist.

## Destination-repository licensing status

The destination repository currently has no top-level license file and GitHub reports no detected repository license. The 1,532 imported Git submodules retain their own upstream repository boundaries and license files; that does not license the destination repository's original code or grant blanket permission to redistribute the submodule contents. Do not infer a project-wide license from the upstream inventory. A project-wide license decision and a source-by-source redistribution review remain release blockers.

A separate Wix site-context check confirms that Terracotta, NoiseGround, and Honest Education are published Wix sites with Velo enabled; MyOutlet and Engzen are also published Wix sites with Velo enabled. WaveWeaver is a published Wix site with Velo disabled. These are site records, not GitHub repositories. A published site or enabled Velo setting does not by itself establish that a service API exists or is callable; no endpoint has been inferred from site metadata.

## Read-only Wix site metadata check

The linked Wix site records and CMS APIs were checked without changing site settings or content. The observations below describe only the queried Wix CMS collections and site settings:

- WaveWeaver: the CMS API reports that the Wix CMS app is not installed; its site context reports Velo disabled. The queried site did not expose a CMS literary catalog.
- Terracotta: Velo is enabled, but the queried custom collection (`japs-rsrs`) contained zero items.
- NoiseGround: the queried Blog/Posts collection contained zero items; its portfolio contained six generic photography entries.
- MyOutlet: the queried Blog/Posts collection contained zero items; other native collections concern the site's media/creator/live-streaming features.
- Engzen: the queried Blog/Posts collection contained zero items. The inspected GitHub repository was identified as the MyOutlet browser extension.
- Honest Education: the queried CMS collections did not expose a fact-checking corpus; the inspected site data included a booking service and contact form.

These site-level observations do not establish whether the corresponding capabilities exist in Astrologically Intelligent's native application code. They do not make third-party APIs a prerequisite, and they do not justify marking a native capability absent. No Wix content or settings were created, altered, or published during this check.
