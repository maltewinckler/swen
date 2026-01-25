"""Enrichment service for search-based text enhancement."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .search import SearchResult, SearXNGAdapter

logger = logging.getLogger(__name__)


def extract_enrichment_text(results: list[SearchResult], max_length: int = 300) -> str:
    """Extract useful text from search results for embedding enhancement."""
    if not results:
        return ""

    texts: list[str] = []
    total_len = 0

    for i, r in enumerate(results):
        if total_len >= max_length:
            break

        # First result's title
        if i == 0 and r.title:
            texts.append(r.title)
            total_len += len(r.title)

        # Add first sentence of content
        if r.content:
            first_sentence = r.content.split(".")[0].strip()
            if len(first_sentence) > 20:
                texts.append(first_sentence)
                total_len += len(first_sentence)

    return " ".join(texts)[:max_length]


@dataclass
class Enrichment:
    """Enrichment data for a merchant."""

    query: str
    text: str


class EnrichmentService:
    """Service for enriching transaction texts with search results."""

    def __init__(self, adapter: SearXNGAdapter):
        self.adapter = adapter

    async def enrich(self, query: str) -> Enrichment | None:
        if not query:
            return None

        results = await self.adapter.search(query)
        if not results:
            logger.debug("No search results for query: %s", query[:50])
            return None

        text = extract_enrichment_text(results)
        if not text:
            return None

        return Enrichment(query=query, text=text)

    async def enrich_batch(
        self,
        queries: list[str],
        rate_limit_seconds: float = 1.0,
    ) -> list[Enrichment | None]:
        """Enrich a batch of queries with rate limiting."""
        results: list[Enrichment | None] = []

        for query in queries:
            result = await self.enrich(query)
            results.append(result)

            # Rate limit (only if we actually searched)
            if result:
                await asyncio.sleep(rate_limit_seconds)

        return results
