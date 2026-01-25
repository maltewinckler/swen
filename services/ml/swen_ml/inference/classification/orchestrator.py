"""Classification pipeline orchestrator.

This module provides the ClassificationOrchestrator, an application service
that coordinates the full classification pipeline for production use.

For evaluation and testing, use the pipeline components directly:
- TextCleaner, PatternMatcher (preprocessing)
- ExampleClassifier, AnchorClassifier (classifiers)
- EnrichmentService (enrichment)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import TransactionInput

from swen_ml.storage import RepositoryFactory

from .context import PipelineContext, TransactionContext
from .result import ClassificationResult
from .tiers import AnchorTier, EnrichmentTier, ExampleTier, PreprocessingTier

if TYPE_CHECKING:
    from swen_ml.inference.shared import SharedInfrastructure

logger = logging.getLogger(__name__)


def build_results(contexts: list[TransactionContext]) -> list[ClassificationResult]:
    """Convert TransactionContexts to ClassificationResults.

    This is a utility function that can be used by both the orchestrator
    and the evaluation module to convert processed contexts to results.

    Args:
        contexts: Processed transaction contexts

    Returns:
        List of ClassificationResult, one per context
    """
    results: list[ClassificationResult] = []

    for ctx in contexts:
        match = ctx.get_classification()

        if match:
            results.append(
                ClassificationResult(
                    transaction_id=ctx.transaction_id,
                    account_id=UUID(match.account_id),
                    account_number=match.account_number,
                    confidence=match.confidence,
                    resolved_by=ctx.resolved_by,
                )
            )
        else:
            # Unresolved - backend decides fallback
            results.append(
                ClassificationResult(
                    transaction_id=ctx.transaction_id,
                    account_id=None,
                    account_number=None,
                    confidence=0.0,
                    resolved_by=None,
                )
            )

    return results


class ClassificationOrchestrator:
    """Application service for classification.

    This orchestrator coordinates the full classification pipeline:
    1. Preprocessing (text cleaning, pattern matching)
    2. Example-based classification (user's historical data)
    3. Online enrichment (SearXNG search)
    4. Anchor-based classification (cold start)

    The orchestrator manages:
    - User-specific data loaded from database per request
    - Pipeline component lifecycle
    - Early exit when transactions are resolved

    Usage:
        # Created once at app startup
        orchestrator = ClassificationOrchestrator(infra)

        # Called per request with database session
        results = await orchestrator.classify(
            session=db_session,
            transactions=txns,
            accounts=accounts,
            user_id=user_id,
        )

    For evaluation/testing, use pipeline components directly instead.
    """

    def __init__(self, infra: SharedInfrastructure) -> None:
        self._infra = infra

    async def classify(
        self,
        session: AsyncSession,
        transactions: list[TransactionInput],
        user_id: UUID,
    ) -> list[ClassificationResult]:
        """Classify a batch of transactions.

        Runs the full classification pipeline:
        1. Preprocessing (text cleaning, pattern matching)
        2. Example classification (user's historical data)
        3. Online enrichment (SearXNG search)
        4. Anchor classification (cold start)

        Args:
            session: Database session for loading user data
            transactions: Transactions to classify
            user_id: User ID for loading user-specific data

        Returns:
            List of ClassificationResult, one per transaction
        """
        n_txns = len(transactions)

        logger.info(
            "Starting classification: user=%s, transactions=%d",
            user_id,
            n_txns,
        )

        # Load user data from database (repos are user-scoped)
        repos = RepositoryFactory(session, user_id)
        pipeline_ctx = await PipelineContext.from_repositories(self._infra, repos)

        n_examples = len(pipeline_ctx.example_store)
        n_anchors = len(pipeline_ctx.anchor_store)
        logger.debug("Loaded user data: %d examples, %d anchors", n_examples, n_anchors)

        # Log anchor account numbers for debugging
        if n_anchors > 0:
            anchor_accounts = pipeline_ctx.anchor_store.account_numbers
            logger.debug("  Anchors: %s", ", ".join(anchor_accounts))

        # Observe new transactions to update noise model
        texts = self._extract_texts(transactions)
        pipeline_ctx.noise_model.observe_batch(texts)

        # Save updated noise model
        await repos.noise.save(
            token_frequencies=dict(pipeline_ctx.noise_model.token_doc_freq),
            document_count=pipeline_ctx.noise_model.doc_count,
        )

        # Initialize transaction contexts
        contexts = [TransactionContext.from_input(txn) for txn in transactions]

        # Build and execute tiers
        anchor_threshold = self._infra.settings.anchor_accept_threshold
        tiers = [
            PreprocessingTier(pipeline_ctx),
            ExampleTier(pipeline_ctx),
            EnrichmentTier(pipeline_ctx.enrichment_service),
            AnchorTier(pipeline_ctx, accept_threshold=anchor_threshold),
        ]

        for tier in tiers:
            await tier.process(contexts)

            # Early exit if all resolved
            if all(c.resolved for c in contexts):
                logger.info("All transactions resolved by %s tier", tier.name)
                break

        # Final summary
        n_resolved = sum(1 for c in contexts if c.resolved)
        logger.info(
            "Classification complete: %d/%d resolved",
            n_resolved,
            n_txns,
        )

        return build_results(contexts)

    @staticmethod
    def _extract_texts(transactions: list[TransactionInput]) -> list[str]:
        texts = []
        for txn in transactions:
            parts = []
            if txn.counterparty_name:
                parts.append(txn.counterparty_name)
            parts.append(txn.purpose)
            texts.append(" ".join(parts))
        return texts
