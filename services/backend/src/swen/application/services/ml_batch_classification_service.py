"""Batch ML classification service for transaction import.

This service orchestrates batch classification of bank transactions
via the ML service, yielding progress events for SSE streaming.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from swen_ml_contracts import TransactionInput

from swen.application.dtos.integration import (
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
)
from swen.domain.banking.repositories import StoredBankTransaction

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchClassificationResult:
    """Result of classifying a single transaction in a batch."""

    transaction_id: UUID
    counter_account_id: UUID | None
    counter_account_number: str | None
    confidence: float
    tier: str
    merchant: str | None
    is_recurring: bool
    recurring_pattern: str | None


@dataclass
class BatchClassificationStats:
    """Statistics from batch classification."""

    total: int
    by_tier: dict[str, int]
    recurring_detected: int
    merchants_extracted: int
    processing_time_ms: int


class MLBatchClassificationService:
    """Service for batch ML classification of transactions.

    Calls the ML service batch endpoint and yields progress events
    for SSE streaming to the frontend.
    """

    def __init__(
        self,
        ml_client: MLServiceClient,
        current_user: CurrentUser,
    ):
        self._ml_client = ml_client
        self._user_id = current_user.user_id

    async def classify_batch_streaming(
        self,
        stored_transactions: list[StoredBankTransaction],
        iban: str,
    ) -> AsyncIterator[
        ClassificationStartedEvent
        | ClassificationProgressEvent
        | ClassificationCompletedEvent
        | dict[UUID, BatchClassificationResult]
    ]:
        """Classify a batch of transactions with streaming progress.

        Yields
        ------
        ClassificationStartedEvent
            When classification begins
        ClassificationProgressEvent
            Progress updates during classification
        ClassificationCompletedEvent
            When classification completes
        dict[UUID, BatchClassificationResult]
            Final result: mapping from bank_transaction_id to classification
        """
        total = len(stored_transactions)
        if total == 0:
            yield {}
            return

        start_time = time.monotonic()

        # Emit start event
        yield ClassificationStartedEvent(iban=iban, total=total)

        # Build ML inputs
        ml_transactions = []
        for stored in stored_transactions:
            tx = stored.transaction
            ml_transactions.append(
                TransactionInput(
                    transaction_id=stored.id,
                    booking_date=tx.booking_date,
                    purpose=tx.purpose or "",
                    amount=tx.amount,
                    counterparty_name=tx.applicant_name,
                    counterparty_iban=tx.applicant_iban,
                )
            )

        # Call ML service batch endpoint
        response = await self._ml_client.classify_batch(
            user_id=self._user_id,
            transactions=ml_transactions,
        )

        if response is None:
            # ML service unavailable - return empty results
            logger.warning("ML service unavailable, returning empty classification")
            yield ClassificationCompletedEvent(
                iban=iban,
                total=total,
                by_tier={"fallback": total},
                processing_time_ms=int((time.monotonic() - start_time) * 1000),
            )
            yield {}
            return

        # Build results mapping
        results: dict[UUID, BatchClassificationResult] = {}

        for i, classification in enumerate(response.classifications):
            # Use account_id directly from ML response (already a UUID)
            account_id = classification.account_id

            if account_id:
                logger.debug(
                    "ML: %s -> %s (tier=%s, conf=%.2f)",
                    classification.account_number,
                    account_id,
                    classification.tier,
                    classification.confidence,
                )
            elif classification.tier != "unresolved":
                logger.warning(
                    "ML returned tier=%s but no account_id for %s",
                    classification.tier,
                    classification.account_number,
                )

            results[classification.transaction_id] = BatchClassificationResult(
                transaction_id=classification.transaction_id,
                counter_account_id=account_id,
                counter_account_number=classification.account_number,
                confidence=classification.confidence,
                tier=classification.tier,
                merchant=classification.merchant,
                is_recurring=classification.is_recurring,
                recurring_pattern=classification.recurring_pattern,
            )

            # Emit progress every 10 transactions or at the end
            if (i + 1) % 10 == 0 or i == len(response.classifications) - 1:
                yield ClassificationProgressEvent(
                    iban=iban,
                    current=i + 1,
                    total=total,
                    last_tier=classification.tier,
                    last_merchant=classification.merchant,
                )

        processing_time_ms = int((time.monotonic() - start_time) * 1000)

        # Count stats
        recurring_count = sum(1 for r in results.values() if r.is_recurring)
        merchant_count = sum(1 for r in results.values() if r.merchant)

        # Emit completion event
        yield ClassificationCompletedEvent(
            iban=iban,
            total=total,
            by_tier=response.stats.by_tier if response.stats else {},  # type: ignore[arg-type]
            recurring_detected=recurring_count,
            merchants_extracted=merchant_count,
            processing_time_ms=processing_time_ms,
        )

        # Yield final results
        yield results

    async def classify_batch(
        self,
        stored_transactions: list[StoredBankTransaction],
        iban: str,
    ) -> tuple[dict[UUID, BatchClassificationResult], BatchClassificationStats]:
        """Classify a batch of transactions without streaming.

        Returns
        -------
        tuple[dict, BatchClassificationStats]
            Results mapping and statistics
        """
        results: dict[UUID, BatchClassificationResult] = {}
        stats = BatchClassificationStats(
            total=len(stored_transactions),
            by_tier={},
            recurring_detected=0,
            merchants_extracted=0,
            processing_time_ms=0,
        )

        async for event in self.classify_batch_streaming(stored_transactions, iban):
            if isinstance(event, dict):
                results = event
            elif isinstance(event, ClassificationCompletedEvent):
                stats = BatchClassificationStats(
                    total=event.total,
                    by_tier=event.by_tier,
                    recurring_detected=event.recurring_detected,
                    merchants_extracted=event.merchants_extracted,
                    processing_time_ms=event.processing_time_ms,
                )

        return results, stats
