"""Pipeline tier implementations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from .classifiers import AnchorClassifier, ExampleClassifier
from .enrichment import EnrichmentService
from .preprocessing import TextCleaner

if TYPE_CHECKING:
    from .context import PipelineContext, TransactionContext


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

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run all preprocessing steps."""
        self._text_cleaner.process_batch(contexts)
        logger.debug("Preprocessing complete: %d transactions", len(contexts))


class ExampleTier(PipelineTier):
    """Example classification tier: matches against user's historical examples."""

    name = "example"

    def __init__(self, pipeline_ctx: PipelineContext):
        self._classifier = ExampleClassifier(pipeline_ctx)

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run example-based classification."""
        await self._classifier.classify_batch(contexts)
        n_resolved = sum(1 for c in contexts if c.resolved)
        logger.info("Example tier: %d/%d resolved", n_resolved, len(contexts))


class EnrichmentTier(PipelineTier):
    """Enrichment tier: enhances unresolved transactions with search data."""

    name = "enrichment"

    def __init__(self, pipeline_ctx: PipelineContext):
        self._service = EnrichmentService(pipeline_ctx)

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Enrich unresolved transactions with search results."""
        n_enriched = await self._service.enrich_batch(contexts)
        if n_enriched > 0:
            logger.info(
                "Enrichment tier: %d/%d enriched",
                n_enriched,
                len([ctx for ctx in contexts if not ctx.resolved]),
            )


class AnchorTier(PipelineTier):
    """Anchor classification tier: matches against account embeddings."""

    name = "anchor"

    def __init__(self, pipeline_ctx: PipelineContext, accept_threshold: float = 0.35):
        self._classifier = AnchorClassifier(pipeline_ctx, accept_threshold)

    async def process(self, contexts: list[TransactionContext]) -> None:
        """Run anchor-based classification on unresolved transactions."""
        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return

        await self._classifier.classify_batch(contexts)
        n_resolved = sum(1 for c in unresolved if c.resolved)
        logger.info("Anchor tier: %d/%d resolved", n_resolved, len(unresolved))
