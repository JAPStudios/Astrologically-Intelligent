#!/usr/bin/env python3
"""Import every public repository from the configured upstream organizations as Git submodules.

Run from the root of a clean Astrologically Intelligent checkout:
    python scripts/import_upstream_orgs.py --dry-run
    GITHUB_TOKEN=... python scripts/import_upstream_orgs.py

The import is resumable: existing submodule URLs are skipped. Archived and forked
public repositories are included. Private repositories are not accessible through
the public organization listing API.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ORGANIZATIONS = (
    "anthropics", "n8n-io", "NousResearch", "odysseus-dev", "openai",
    "openclaw", "paperclipai", "perplexityai", "xai-org",
)
API_ROOT = "https://api.github.com"


def fetch_page(org: str, page: int, token: str | None = None) -> list[dict]:
    if org not in ORGANIZATIONS:
        raise ValueError(f"Organization is outside the requested scope: {org}")
    query = urllib.parse.urlencode({"type": "public", "per_page": 100, "page": page})
    request = urllib.request.Request(
        f"{API_ROOT}/orgs/{org}/repos?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError(f"Could not list public repositories for {org}: {exc}") from exc
    if not isinstance(result, list):
        raise RuntimeError(f"GitHub returned an invalid repository listing for {org}")
    return result


def list_repositories(orgs: tuple[str, ...], token: str | None = None) -> list[dict]:
    repositories: list[dict] = []
    for org in orgs:
        page = 1
        while True:
            batch = fetch_page(org, page, token)
            if not batch:
                break
            for item in batch:
                if item.get("private") is True or item.get("owner", {}).get("login", "").lower() != org.lower():
                    continue
                name = item.get("name", "")
                branch = item.get("default_branch")
                clone_url = item.get("clone_url")
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or not clone_url:
                    continue
                repositories.append({
                    "org": org, "name": name, "branch": branch,
                    "clone_url": clone_url, "archived": bool(item.get("archived")),
                    "fork": bool(item.get("fork")), "empty": not branch or int(item.get("size") or 0) == 0,
                })
            if len(batch) < 100:
                break
            page += 1
    return repositories


def existing_submodule_urls(root: Path) -> set[str]:
    gitmodules = root / ".gitmodules"
    if not gitmodules.is_file():
        return set()
    result = subprocess.run(
        ["git", "config", "--file", str(gitmodules), "--get-regexp", r"^submodule\..*\.url$"],
        cwd=root, check=False, capture_output=True, text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "Could not inspect .gitmodules")
    return {line.split(None, 1)[1].removesuffix(".git") for line in result.stdout.splitlines() if " " in line}


def import_repositories(root: Path, repositories: list[dict], dry_run: bool = False,
                        limit: int | None = None) -> tuple[int, int]:
    known = existing_submodule_urls(root)
    added = skipped = 0
    for repository in repositories:
        url = repository["clone_url"].removesuffix(".git")
        path = root / "upstream" / repository["org"] / repository["name"]
        if url in known:
            skipped += 1
            continue
        if repository.get("empty"):
            print(f"[skip empty] {repository['org']}/{repository['name']}")
            skipped += 1
            continue
        if limit is not None and added >= limit:
            break
        relative_path = path.relative_to(root).as_posix()
        command = ["git", "submodule", "add", "--depth", "1"]
        if repository.get("branch"):
            command += ["--branch", repository["branch"]]
        command += [repository["clone_url"], relative_path]
        print(f"{'[dry-run] ' if dry_run else ''}{relative_path} <- {url}")
        if not dry_run:
            subprocess.run(command, cwd=root, check=True)
        known.add(url)
        added += 1
    return added, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", action="append", choices=ORGANIZATIONS,
                        help="Import one organization; repeat to select several. Default: all nine.")
    parser.add_argument("--dry-run", action="store_true", help="List imports without cloning repositories.")
    parser.add_argument("--limit", type=int, help="Stop after adding this many new submodules.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    root = Path.cwd().resolve()
    if not (root / ".git").exists():
        parser.error("Run this command from the root of a Git checkout.")
    orgs = tuple(args.org or ORGANIZATIONS)
    try:
        repositories = list_repositories(orgs, os.getenv("GITHUB_TOKEN"))
        added, skipped = import_repositories(root, repositories, args.dry_run, args.limit)
    except Exception as exc:
        print(f"Import stopped: {exc}", file=sys.stderr)
        return 1
    print(f"Repository listing: {len(repositories)} public repositories.")
    print(f"Submodules {'planned' if args.dry_run else 'added'}: {added}; already present: {skipped}.")
    print(f"IMPORT_ADDED={added} IMPORT_SKIPPED={skipped}")
    if args.dry_run:
        print("Run without --dry-run to clone and stage the source repositories.")
    else:
        print("Review .gitmodules and the staged gitlinks, then commit the import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
