"""ML Service adapter implementing the application port."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator

from swen_ml_contracts import AccountOption, StoreExampleRequest, TransactionInput

from swen.application.ports.ml_service import (
    AccountForClassification,
    BatchClassificationResult,
    ClassificationProgress,
    ClassificationResult,
    MLServicePort,
    TransactionExample,
    TransactionForClassification,
)

if TYPE_CHECKING:
    from uuid import UUID

    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class MLServiceAdapter(MLServicePort):
    """Infrastructure adapter that implements MLServicePort.

    Translates domain objects to ML contracts and delegates to the HTTP client.
    """

    def __init__(self, client: MLServiceClient):
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    def submit_example(self, example: TransactionExample) -> None:
        """Submit a posted transaction as a training example (fire-and-forget)."""
        if not self._client.enabled:
            return

        request = StoreExampleRequest(
            transaction_id=example.transaction_id,
            counterparty_name=example.counterparty_name,
            counterparty_iban=example.counterparty_iban,
            purpose=example.purpose,
            amount=example.amount,
            account_id=example.account_id,
            account_number=example.account_number,
        )

        self._client.store_example_fire_and_forget(example.user_id, request)
        logger.debug(
            "Submitted ML example: txn=%s -> account=%s",
            example.transaction_id,
            example.account_number,
        )

    async def classify_batch(
        self,
        user_id: UUID,
        transactions: list[TransactionForClassification],
        accounts: list[AccountForClassification],
    ) -> BatchClassificationResult | None:
        """Classify a batch of transactions."""
        if not self._client.enabled:
            return None

        # Convert domain objects to ML contracts
        ml_transactions = [
            TransactionInput(
                transaction_id=txn.transaction_id,
                booking_date=txn.booking_date,
                counterparty_name=txn.counterparty_name,
                counterparty_iban=txn.counterparty_iban,
                purpose=txn.purpose,
                amount=txn.amount,
            )
            for txn in transactions
        ]

        ml_accounts = [
            AccountOption(
                account_id=acc.account_id,
                account_number=acc.account_number,
                name=acc.name,
                account_type=acc.account_type,
                description=acc.description,
            )
            for acc in accounts
        ]

        result = await self._client.classify_batch(
            user_id=user_id,
            transactions=ml_transactions,
            available_accounts=ml_accounts,
        )

        if result is None:
            return None

        # Convert ML response to domain objects
        classifications = [
            ClassificationResult(
                transaction_id=clf.transaction_id,
                account_id=clf.account_id,
                account_number=clf.account_number,
                confidence=clf.confidence,
                tier=clf.tier,
                merchant=clf.merchant,
                is_recurring=clf.is_recurring,
                recurring_pattern=clf.recurring_pattern,
            )
            for clf in result.classifications
        ]

        return BatchClassificationResult(
            classifications=classifications,
            processing_time_ms=result.processing_time_ms,
            total=result.stats.total,
            by_tier={str(k): v for k, v in result.stats.by_tier.items()},
            recurring_detected=result.stats.recurring_detected,
            merchants_extracted=result.stats.merchants_extracted,
        )

    async def classify_batch_streaming(
        self,
        user_id: UUID,
        transactions: list[TransactionForClassification],
        accounts: list[AccountForClassification],
    ) -> AsyncIterator[ClassificationProgress | BatchClassificationResult]:
        """Classify batch with streaming progress updates."""
        if not self._client.enabled:
            return

        # Convert domain objects to ML contracts
        ml_transactions = [
            TransactionInput(
                transaction_id=txn.transaction_id,
                booking_date=txn.booking_date,
                counterparty_name=txn.counterparty_name,
                counterparty_iban=txn.counterparty_iban,
                purpose=txn.purpose,
                amount=txn.amount,
            )
            for txn in transactions
        ]

        ml_accounts = [
            AccountOption(
                account_id=acc.account_id,
                account_number=acc.account_number,
                name=acc.name,
                account_type=acc.account_type,
                description=acc.description,
            )
            for acc in accounts
        ]

        async for event in self._client.classify_batch_streaming(
            user_id=user_id,
            transactions=ml_transactions,
            available_accounts=ml_accounts,
        ):
            event_type = event.get("type")

            if event_type == "progress":
                yield ClassificationProgress(
                    current=event.get("current", 0),
                    total=event.get("total", 0),
                    last_tier=event.get("last_tier"),
                    last_merchant=event.get("last_merchant"),
                )
            elif event_type == "result":
                # Parse full result
                classifications = [
                    ClassificationResult(
                        transaction_id=clf["transaction_id"],
                        account_id=clf["account_id"],
                        account_number=clf["account_number"],
                        confidence=clf["confidence"],
                        tier=clf["tier"],
                        merchant=clf.get("merchant"),
                        is_recurring=clf.get("is_recurring", False),
                        recurring_pattern=clf.get("recurring_pattern"),
                    )
                    for clf in event.get("classifications", [])
                ]

                stats = event.get("stats", {})
                yield BatchClassificationResult(
                    classifications=classifications,
                    processing_time_ms=event.get("processing_time_ms", 0),
                    total=stats.get("total", 0),
                    by_tier=stats.get("by_tier", {}),
                    recurring_detected=stats.get("recurring_detected", 0),
                    merchants_extracted=stats.get("merchants_extracted", 0),
                )

    async def embed_accounts(
        self,
        user_id: UUID,
        accounts: list[AccountForClassification],
    ) -> bool:
        """Compute and store anchor embeddings for accounts."""
        if not self._client.enabled:
            return False

        ml_accounts = [
            AccountOption(
                account_id=acc.account_id,
                account_number=acc.account_number,
                name=acc.name,
                account_type=acc.account_type,
                description=acc.description,
            )
            for acc in accounts
        ]

        result = await self._client.embed_accounts(user_id, ml_accounts)
        return result is not None and result.embedded > 0
