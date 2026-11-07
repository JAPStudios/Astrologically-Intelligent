"""Agent tools backed by Peanut Browsing's first-party search index."""
from __future__ import annotations

import json

from src.peanut_browsing import PeanutBrowsingClient, PeanutBrowsingError


class PeanutWebSearchTool:
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        try:
            payload = json.loads(content) if content.strip().startswith("{") else {"query": content}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"error": "Invalid Peanut Browsing search arguments.", "exit_code": 1}
        if not isinstance(payload, dict):
            return {"error": "Peanut Browsing search arguments must be an object.", "exit_code": 1}
        query = payload.get("query") or payload.get("q")
        try:
            limit = payload.get("limit", 20)
            offset = payload.get("offset", 0)
            result = await PeanutBrowsingClient().search(query, limit=limit, offset=offset)
        except (PeanutBrowsingError, ValueError) as exc:
            return {"error": str(exc), "exit_code": 1}
        rows = result["results"]
        if not rows:
            return {
                "output": f"Peanut Browsing found no indexed pages matching: {query}",
                "exit_code": 0,
                "evidence_status": "empty",
                "total_results": result["totalResults"],
            }
        lines = [f"Peanut Browsing search results for: {query}", ""]
        sources = []
        for index, row in enumerate(rows, 1):
            lines.extend([
                f"[{index}] {row['title']}",
                f"URL: {row['url']}",
                f"Snippet: {row['snippet']}",
                f"Index score: {row['score']:.6f}",
                "",
            ])
            sources.append({"title": row["title"], "url": row["url"]})
        output = "\n".join(lines).rstrip()
        output += "\n\n<!-- SOURCES:" + json.dumps(sources, ensure_ascii=False) + " -->"
        return {
            "output": output,
            "exit_code": 0,
            "evidence_status": "available",
            "engine": "Peanut Browsing",
            "total_results": result["totalResults"],
        }


class PeanutCrawlTool:
    async def execute(self, content: str, ctx: dict | None = None) -> dict:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"error": "Peanut Browsing crawl arguments must be valid JSON.", "exit_code": 1}
        if not isinstance(payload, dict):
            return {"error": "Peanut Browsing crawl arguments must be an object.", "exit_code": 1}
        try:
            result = await PeanutBrowsingClient().crawl(
                payload.get("url"), max_pages=payload.get("max_pages", 10)
            )
        except (PeanutBrowsingError, ValueError) as exc:
            return {"error": str(exc), "exit_code": 1}
        return {
            "output": (
                "Peanut Browsing crawl completed. "
                f"Visited {result.get('visited', 0)} pages and indexed "
                f"{result.get('indexed', 0)} pages. "
                f"Discovered {result.get('sitemapPagesDiscovered', 0)} sitemap pages."
            ),
            "exit_code": 0,
            "engine": "Peanut Browsing",
            "crawl": result,
        }
