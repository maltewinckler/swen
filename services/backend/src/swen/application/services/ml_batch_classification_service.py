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


@dataclass
class _ChunkProcessingState:
    """Mutable state for chunk processing."""

    results: dict[UUID, BatchClassificationResult]
    tier_counts: dict[str, int]
    processed: int
    last_tier: str | None
    last_merchant: str | None
    ml_unavailable: bool

    @classmethod
    def initial(cls) -> _ChunkProcessingState:
        return cls(
            results={},
            tier_counts={},
            processed=0,
            last_tier=None,
            last_merchant=None,
            ml_unavailable=False,
        )


class MLBatchClassificationService:
    """Service for batch ML classification of transactions."""

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
        chunk_size: int = 5,
    ) -> AsyncIterator[
        ClassificationStartedEvent
        | ClassificationProgressEvent
        | ClassificationCompletedEvent
        | dict[UUID, BatchClassificationResult]
    ]:
        """Classify a batch of transactions with streaming progress.

        Processes transactions in chunks to provide real-time progress feedback.
        Each chunk is sent to the ML service separately, with progress events
        emitted after each chunk completes.

        Parameters
        ----------
        stored_transactions
            Transactions to classify
        iban
            Account IBAN for progress events
        chunk_size
            Number of transactions per chunk (default: 5)

        Yields
        ------
        ClassificationStartedEvent
            When classification begins
        ClassificationProgressEvent
            Progress updates after each chunk
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
        yield ClassificationStartedEvent(iban=iban, total=total)

        ml_transactions = self._build_ml_inputs(stored_transactions)
        state = _ChunkProcessingState.initial()

        async for progress_event in self._process_chunks(
            ml_transactions, iban, chunk_size, state
        ):
            yield progress_event

        self._handle_remaining_fallbacks(ml_transactions, state)

        yield self._build_completion_event(
            iban=iban,
            results=state.results,
            tier_counts=state.tier_counts,
            start_time=start_time,
        )
        yield state.results

    def _build_ml_inputs(
        self,
        stored_transactions: list[StoredBankTransaction],
    ) -> list[TransactionInput]:
        return [
            TransactionInput(
                transaction_id=stored.id,
                booking_date=stored.transaction.booking_date,
                purpose=stored.transaction.purpose or "",
                amount=stored.transaction.amount,
                counterparty_name=stored.transaction.applicant_name,
                counterparty_iban=stored.transaction.applicant_iban,
            )
            for stored in stored_transactions
        ]

    async def _process_chunks(
        self,
        ml_transactions: list[TransactionInput],
        iban: str,
        chunk_size: int,
        state: _ChunkProcessingState,
    ) -> AsyncIterator[ClassificationProgressEvent]:
        total = len(ml_transactions)

        for chunk_start in range(0, total, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total)
            chunk = ml_transactions[chunk_start:chunk_end]

            await self._process_single_chunk(chunk, chunk_start, chunk_end, state)
            state.processed = chunk_end

            yield ClassificationProgressEvent(
                iban=iban,
                current=state.processed,
                total=total,
                last_tier=state.last_tier,
                last_merchant=state.last_merchant,
            )

            if state.ml_unavailable:
                break

    async def _process_single_chunk(
        self,
        chunk: list[TransactionInput],
        chunk_start: int,
        chunk_end: int,
        state: _ChunkProcessingState,
    ) -> None:
        response = await self._ml_client.classify_batch(
            user_id=self._user_id,
            transactions=chunk,
        )

        if response is None:
            state.ml_unavailable = True
            logger.warning(
                "ML service unavailable at chunk %d-%d",
                chunk_start,
                chunk_end,
            )
            self._add_fallback_results(chunk, state)
        else:
            self._process_chunk_response(response, state)

    def _add_fallback_results(
        self,
        transactions: list[TransactionInput],
        state: _ChunkProcessingState,
    ) -> None:
        for ml_txn in transactions:
            state.results[ml_txn.transaction_id] = self._create_fallback_result(
                ml_txn.transaction_id
            )
            state.tier_counts["fallback"] = state.tier_counts.get("fallback", 0) + 1

    def _create_fallback_result(
        self,
        transaction_id: UUID,
    ) -> BatchClassificationResult:
        return BatchClassificationResult(
            transaction_id=transaction_id,
            counter_account_id=None,
            counter_account_number=None,
            confidence=0.0,
            tier="fallback",
            merchant=None,
            is_recurring=False,
            recurring_pattern=None,
        )

    def _process_chunk_response(
        self,
        response: object,
        state: _ChunkProcessingState,
    ) -> None:
        for classification in response.classifications:  # type: ignore[attr-defined]
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

            state.results[classification.transaction_id] = BatchClassificationResult(
                transaction_id=classification.transaction_id,
                counter_account_id=account_id,
                counter_account_number=classification.account_number,
                confidence=classification.confidence,
                tier=classification.tier,
                merchant=classification.merchant,
                is_recurring=classification.is_recurring,
                recurring_pattern=classification.recurring_pattern,
            )

            tier = classification.tier
            state.tier_counts[tier] = state.tier_counts.get(tier, 0) + 1
            state.last_tier = tier
            state.last_merchant = classification.merchant

    def _handle_remaining_fallbacks(
        self,
        ml_transactions: list[TransactionInput],
        state: _ChunkProcessingState,
    ) -> None:
        if state.ml_unavailable and state.processed < len(ml_transactions):
            self._add_fallback_results(ml_transactions[state.processed :], state)

    def _build_completion_event(
        self,
        iban: str,
        results: dict[UUID, BatchClassificationResult],
        tier_counts: dict[str, int],
        start_time: float,
    ) -> ClassificationCompletedEvent:
        """Build the completion event with statistics."""
        processing_time_ms = int((time.monotonic() - start_time) * 1000)
        recurring_count = sum(1 for r in results.values() if r.is_recurring)
        merchant_count = sum(1 for r in results.values() if r.merchant)

        return ClassificationCompletedEvent(
            iban=iban,
            total=len(results),
            by_tier=tier_counts,
            recurring_detected=recurring_count,
            merchants_extracted=merchant_count,
            processing_time_ms=processing_time_ms,
        )

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
