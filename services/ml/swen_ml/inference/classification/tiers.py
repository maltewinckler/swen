"""Pipeline tier implementations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from .classifiers import AnchorClassifier, ExampleClassifier
from .preprocessing import PatternMatcher, TextCleaner

if TYPE_CHECKING:
    from .context import PipelineContext, TransactionContext
    from .enrichment import EnrichmentService


class PipelineTier(Protocol):
    """Interface for pipeline tiers.

    Each tier processes a batch of transactions, mutating contexts in place.
    Tiers can be preprocessing, classification, or enrichment.
    """

    name: str

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Process batch, mutating contexts in place."""
        ...

logger = logging.getLogger(__name__)


class PreprocessingTier(PipelineTier):
    """Preprocessing tier: text cleaning and pattern matching."""

    name = "preprocessing"

    def __init__(self, pipeline_ctx: PipelineContext):
        self._text_cleaner = TextCleaner(pipeline_ctx)
        self._pattern_matcher = PatternMatcher()

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run all preprocessing steps."""
        self._text_cleaner.process_batch(contexts)
        self._pattern_matcher.process_batch(contexts)

        # Log cleaned text for each transaction
        for ctx in contexts:
            logger.debug(
                "  Preprocessed: counterparty=%r purpose=%r keywords=%s",
                ctx.cleaned_counterparty,
                (ctx.cleaned_purpose[:50] + "...") if ctx.cleaned_purpose else None,
                ctx.matched_keywords or [],
            )
        logger.debug("Preprocessing complete: %d transactions", len(contexts))


class ExampleTier(PipelineTier):
    """Example classification tier: matches against user's historical examples."""

    name = "example"

    def __init__(self, pipeline_ctx: PipelineContext):
        self._classifier = ExampleClassifier()
        self._pipeline_ctx = pipeline_ctx

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run example-based classification."""
        await self._classifier.classify_batch(contexts, self._pipeline_ctx)
        n_resolved = sum(1 for c in contexts if c.resolved)
        logger.info("Example tier: %d/%d resolved", n_resolved, len(contexts))


class EnrichmentTier(PipelineTier):
    """Enrichment tier: enhances unresolved transactions with search data."""

    name = "enrichment"

    def __init__(self, enrichment_service: EnrichmentService | None):
        self._service = enrichment_service

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Enrich unresolved transactions with search results."""
        if not self._service:
            logger.debug("Enrichment skipped: no enrichment service")
            return

        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return

        n_enriched = 0
        for ctx in unresolved:
            query = ctx.cleaned_counterparty
            if query:
                enrichment = await self._service.enrich(query)
                if enrichment:
                    ctx.search_enrichment = enrichment.text
                    text = enrichment.text
                    preview = text[:80] + "..." if len(text) > 80 else text
                    logger.debug("  Enriched %r -> %r", query, preview)
                    n_enriched += 1
                else:
                    logger.debug("  No enrichment for %r", query)

        logger.info("Enrichment tier: %d/%d enriched", n_enriched, len(unresolved))


class AnchorTier(PipelineTier):
    """Anchor classification tier: matches against account embeddings."""

    name = "anchor"

    def __init__(self, pipeline_ctx: PipelineContext, accept_threshold: float = 0.35):
        self._classifier = AnchorClassifier(accept_threshold=accept_threshold)
        self._pipeline_ctx = pipeline_ctx

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run anchor-based classification on unresolved transactions."""
        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return

        await self._classifier.classify_batch(unresolved, self._pipeline_ctx)
        n_resolved = sum(1 for c in unresolved if c.resolved)
        logger.info("Anchor tier: %d/%d resolved", n_resolved, len(unresolved))
