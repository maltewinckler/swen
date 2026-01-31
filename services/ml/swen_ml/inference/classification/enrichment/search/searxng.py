from __future__ import annotations

from typing import Any

import httpx

from .port import SearchPort, SearchResult


class SearXNGAdapter(SearchPort):
    """SearXNG search adapter."""

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        timeout: float = 10.0,
        language: str = "de",
        max_results: int = 1,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.language = language
        self.max_results = max_results

    def _parse_web_results(
        self,
        results: list[SearchResult],
        data: dict[str, Any],
    ) -> list[SearchResult]:
        for item in data.get("results", []):
            if len(results) >= self.max_results:
                break
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    score=float(item.get("score", 0.0)),
                )
            )
        return results

    def _parse_infobox_results(
        self,
        results: list[SearchResult],
        data: dict[str, Any],
    ) -> list[SearchResult]:
        remaining = self.max_results - len(results)
        if remaining > 0:
            for item in data.get("infoboxes", [])[:remaining]:
                results.append(
                    SearchResult(
                        title=item.get("infobox", ""),
                        content=item.get("content", ""),
                        url=item.get("id", ""),
                        score=1.0,  # Lower score for infoboxes
                    )
                )
        return results

    def _parse_response(self, data: dict[str, Any]) -> list[SearchResult]:
        results: list[SearchResult] = []
        results = self._parse_web_results(results, data)
        results = self._parse_infobox_results(results, data)
        return results

    async def search(self, query: str) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": self.language,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException):
                return []

        return self._parse_response(data)

    def search_sync(self, query: str) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        with httpx.Client(timeout=self.timeout) as client:
            try:
                resp = client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": self.language,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException):
                return []

        return self._parse_response(data)
