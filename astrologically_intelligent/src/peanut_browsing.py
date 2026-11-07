"""First-party Peanut Browsing search and crawl client.

This client speaks Peanut Browsing's documented index contract directly.
It deliberately does not substitute a third-party search provider when the
Peanut index is unavailable or has no matching pages.
"""
from __future__ import annotations

import ipaddress
import math
import os
from urllib.parse import urlsplit

import httpx


class PeanutBrowsingError(RuntimeError):
    """A configuration, transport or response error from Peanut Browsing."""


class PeanutBrowsingClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        *,
        timeout: float = 20.0,
        client_factory=httpx.AsyncClient,
        sync_client_factory=httpx.Client,
    ) -> None:
        self.base_url = (base_url if base_url is not None else os.getenv("PEANUT_SEARCH_API_URL", "")).strip().rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("PEANUT_SEARCH_API_KEY", "")
        self.timeout = timeout
        self.client_factory = client_factory
        self.sync_client_factory = sync_client_factory

    def _configuration(self) -> tuple[str, dict[str, str]]:
        if not self.base_url or not self.api_key:
            raise PeanutBrowsingError(
                "Peanut Browsing is not configured. Set PEANUT_SEARCH_API_URL "
                "to its HTTPS index gateway and PEANUT_SEARCH_API_KEY to the "
                "gateway key."
            )
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise PeanutBrowsingError("PEANUT_SEARCH_API_URL must be an HTTP(S) base URL without credentials, query or fragment.")
        if parsed.scheme != "https":
            try:
                address = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                address = None
            if not (parsed.hostname in {"localhost"} or (address and address.is_loopback)):
                raise PeanutBrowsingError("Peanut Browsing must use HTTPS outside loopback development.")
        return self.base_url, {"X-API-Key": self.api_key, "Accept": "application/json"}

    async def _request(self, method: str, path: str, *, params=None, json_body=None) -> dict:
        base_url, headers = self._configuration()
        try:
            async with self.client_factory(timeout=self.timeout, follow_redirects=False) as client:
                response = await client.request(
                    method, f"{base_url}/index/{path}", headers=headers,
                    params=params, json=json_body,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise PeanutBrowsingError(
                f"Peanut Browsing returned HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise PeanutBrowsingError(f"Peanut Browsing request failed: {type(exc).__name__}.") from exc
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise PeanutBrowsingError("Peanut Browsing returned an invalid or unsuccessful response.")
        return payload

    def _request_sync(self, method: str, path: str, *, params=None, json_body=None) -> dict:
        base_url, headers = self._configuration()
        try:
            with self.sync_client_factory(timeout=self.timeout, follow_redirects=False) as client:
                response = client.request(
                    method, f"{base_url}/index/{path}", headers=headers,
                    params=params, json=json_body,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise PeanutBrowsingError(
                f"Peanut Browsing returned HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise PeanutBrowsingError(f"Peanut Browsing request failed: {type(exc).__name__}.") from exc
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise PeanutBrowsingError("Peanut Browsing returned an invalid or unsuccessful response.")
        return payload

    @staticmethod
    def _normalize_search_payload(payload: dict) -> dict:
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise PeanutBrowsingError("Peanut Browsing search response did not contain a results list.")
        results = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = row.get("url")
            if not isinstance(url, str):
                continue
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                continue
            score = row.get("score", 0.0)
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 0.0
            if not math.isfinite(score):
                score = 0.0
            results.append({
                "title": str(row.get("title") or parsed.hostname)[:500],
                "url": url,
                "snippet": str(row.get("snippet") or "")[:4000],
                "score": score,
                "engine": "Peanut Browsing",
            })
        total = payload.get("totalResults", len(results))
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            total = len(results)
        return {"results": results, "totalResults": total}

    @staticmethod
    def _validate_search_arguments(query: str, limit: int, offset: int) -> str:
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError("Search query must contain 1–200 characters.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("Search limit must be an integer from 1 to 50.")
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 100_000:
            raise ValueError("Search offset must be an integer from 0 to 100000.")
        return query.strip()

    async def search(self, query: str, *, limit: int = 20, offset: int = 0) -> dict:
        query = self._validate_search_arguments(query, limit, offset)
        payload = await self._request(
            "GET", "search", params={"q": query, "limit": limit, "offset": offset}
        )
        return self._normalize_search_payload(payload)

    def search_sync(self, query: str, *, limit: int = 20, offset: int = 0) -> dict:
        """Synchronous search entry point for the app's provider registry."""
        query = self._validate_search_arguments(query, limit, offset)
        payload = self._request_sync(
            "GET", "search", params={"q": query, "limit": limit, "offset": offset}
        )
        return self._normalize_search_payload(payload)

    async def crawl(self, url: str, *, max_pages: int = 10) -> dict:
        if not isinstance(url, str) or len(url) > 2048:
            raise ValueError("A public website URL is required.")
        parsed = urlsplit(url.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.hostname.lower() == "localhost"
            or parsed.hostname.lower().endswith((".localhost", ".local", ".internal", ".test", ".invalid"))
        ):
            raise ValueError("Only public HTTP(S) website URLs can be submitted to Peanut Browsing.")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("Private, loopback and reserved network addresses cannot be indexed.")
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 25:
            raise ValueError("max_pages must be an integer from 1 to 25.")
        return await self._request("POST", "crawl", json_body={"url": url.strip(), "maxPages": max_pages})
