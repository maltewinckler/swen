"""Enrichment service for search-based text enhancement."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .search import SearchResult

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        PipelineContext,
        TransactionContext,
    )

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
    """Enrichment data for a transaction."""

    cleaned_counterparty: str
    cleaned_purpose: str
    text: str
    source: Literal["keyword", "search"]

    def log(self) -> None:
        cleaned_counterparty = self.cleaned_counterparty
        cleaned_purpose = self.cleaned_purpose
        text_preview = self.text[:80] + "..." if len(self.text) > 80 else self.text

        purpose_preview = cleaned_purpose[:20] if cleaned_purpose else ""
        counterparty_preview = cleaned_counterparty[:20] if cleaned_counterparty else ""
        logger.debug(
            "  Enriched [%s] %r / %r -> %r",
            self.source,
            counterparty_preview,
            purpose_preview,
            text_preview,
        )


class EnrichmentService:
    """Service for enriching transaction texts with keywords or search results."""

    def __init__(self, pipeline_ctx: PipelineContext):
        self.search_adapter = pipeline_ctx.searxng_adapter
        self.keyword_adapter = pipeline_ctx.keyword_adapter

    def _keyword_enrich(
        self,
        cleaned_counterparty: str,
        cleaned_purpose: str,
    ) -> Enrichment | None:
        """Try keyword-based enrichment on combined text."""
        if not self.keyword_adapter:
            return None

        # Combine counterparty and purpose for keyword matching
        query = " ".join(filter(None, [cleaned_counterparty, cleaned_purpose]))
        keyword_text = self.keyword_adapter.enrich(query)

        if not keyword_text:
            return None
        return Enrichment(
            cleaned_counterparty=cleaned_counterparty,
            cleaned_purpose=cleaned_purpose,
            text=keyword_text,
            source="keyword",
        )

    async def _search_enrich(
        self,
        cleaned_counterparty: str,
        cleaned_purpose: str,
    ) -> Enrichment | None:
        """
        Try search-based enrichment using counterparty.

        This should ease the load on the search backend and prevent some easy
        cases where a transaction to your landlord has 'Miete' in the purpose.
        The search would lookup the name of your landlord which is probably
        a private person which adds noise to a rather easy case.
        """
        if not self.search_adapter or not cleaned_counterparty:
            return None

        query = cleaned_counterparty
        results = await self.search_adapter.search(query)

        if not results:
            return None

        text = extract_enrichment_text(results)
        if not text:
            return None

        await asyncio.sleep(1.0)  # Rate limiting for search backend
        return Enrichment(
            cleaned_counterparty=cleaned_counterparty,
            cleaned_purpose=cleaned_purpose,
            text=text,
            source="search",
        )

    async def enrich(self, ctx: TransactionContext) -> bool:
        cleaned_counterparty = ctx.cleaned_counterparty or ""
        cleaned_purpose = ctx.cleaned_purpose or ""

        if not cleaned_counterparty and not cleaned_purpose:
            return False

        # Try keyword enrichment first
        enrichment = self._keyword_enrich(cleaned_counterparty, cleaned_purpose)
        if enrichment:
            enrichment.log()
            ctx.search_enrichment = enrichment.text
            return True

        # Fall back to search enrichment
        enrichment = await self._search_enrich(cleaned_counterparty, cleaned_purpose)
        if enrichment:
            enrichment.log()
            ctx.search_enrichment = enrichment.text
            return True

        logger.debug(
            "  No enrichment for %r / %r",
            cleaned_counterparty[:20] if cleaned_counterparty else "",
            cleaned_purpose[:20] if cleaned_purpose else "",
        )
        return False

    async def enrich_batch(
        self,
        contexts: list[TransactionContext],
    ) -> int:
        # Early return if no adapters available
        if not self.search_adapter and not self.keyword_adapter:
            return 0

        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return 0

        n_enriched = 0
        for ctx in unresolved:
            # Check if context has any text to enrich
            if not ctx.cleaned_counterparty and not ctx.cleaned_purpose:
                continue

            # Enrich and track if search was used
            enriched = await self.enrich(ctx)
            if enriched:
                n_enriched += 1

        return n_enriched
