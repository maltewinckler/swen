"""Reclassify draft transactions using ML classification."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

from swen.application.dtos.accounting import (
    ReclassifiedTransactionDetail,
    ReclassifyCompletedEvent,
    ReclassifyFailedEvent,
    ReclassifyProgressEvent,
    ReclassifyResultDTO,
    ReclassifyStartedEvent,
    ReclassifyTransactionEvent,
)
from swen.application.dtos.integration import (
    ClassificationProgressEvent,
)
from swen.application.services import MLBatchClassificationService
from swen.application.services.ml_classification_application_service import (
    MLClassificationApplicationService,
    has_fallback_counter_account,
)
from swen.domain.accounting.value_objects import TransactionSource

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.services.ml_batch_classification_service import (
        BatchClassificationResult,
    )
    from swen.domain.accounting.aggregates import Transaction
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)

# MLBatchClassificationService currently requires an IBAN-like label for its
# generic classification progress events. Reclassification operates across draft
# transactions rather than a single bank account, so this is only a scope label.
_RECLASSIFY_PROGRESS_SCOPE = "reclassify"

ReclassifyStreamingEvent = (
    ReclassifyStartedEvent
    | ReclassifyProgressEvent
    | ReclassifyTransactionEvent
    | ReclassifyCompletedEvent
    | ReclassifyFailedEvent
    | ReclassifyResultDTO
)


@dataclass(frozen=True)
class _ReclassificationSummary:
    reclassified: int
    unchanged: int
    failed: int
    details: tuple[ReclassifiedTransactionDetail, ...]


class ReclassifyDraftsCommand:
    """Re-run ML classification on draft bank-import transactions.

    This command loads draft transactions, sends them through the ML
    classification service, and updates counter-accounts where the ML
    produces a different (and valid) classification.

    Designed as an async generator for SSE streaming — yields progress
    events after each ML chunk and after each transaction update.
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        ml_classification_service: MLBatchClassificationService,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._ml_service = ml_classification_service

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_client: MLServiceClient,
    ) -> ReclassifyDraftsCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            ml_classification_service=MLBatchClassificationService(
                ml_client=ml_client,
                current_user=factory.current_user,
            ),
        )

    async def execute_streaming(
        self,
        transaction_ids: list[UUID] | None = None,
        reclassify_all: bool = False,
        only_fallback: bool = False,
    ) -> AsyncIterator[ReclassifyStreamingEvent]:
        """Reclassify drafts with streaming progress events.

        Yields
        ------
        ReclassifyStartedEvent
            When reclassification begins
        ReclassifyProgressEvent
            After each ML classification chunk
        ReclassifyTransactionEvent
            For each transaction that was reclassified
        ReclassifyCompletedEvent
            When reclassification finishes
        ReclassifyFailedEvent
            When reclassification fails unexpectedly
        ReclassifyResultDTO
            Final result (last yield)
        """
        try:
            drafts = await self._load_drafts(
                transaction_ids=transaction_ids,
                reclassify_all=reclassify_all,
                only_fallback=only_fallback,
            )
            async for event in self._run_reclassification(drafts):
                yield event

        except Exception as e:
            logger.exception("Reclassification failed: %s", e)
            yield ReclassifyFailedEvent(error=str(e))

    async def _run_reclassification(
        self,
        drafts: list[Transaction],
    ) -> AsyncIterator[
        ReclassifyStartedEvent
        | ReclassifyProgressEvent
        | ReclassifyTransactionEvent
        | ReclassifyCompletedEvent
        | ReclassifyResultDTO
    ]:
        """Run the full reclassification flow for the given drafts."""
        if not drafts:
            for event in self._build_result_events(total=0):
                yield event
            return

        yield ReclassifyStartedEvent(total=len(drafts))

        classifications: dict[UUID, BatchClassificationResult] = {}
        async for event in self._stream_classifications(drafts):
            if isinstance(event, ReclassifyProgressEvent):
                yield event
                continue
            classifications = event

        summary = None
        async for event in self._apply_classifications_streaming(
            drafts,
            classifications,
        ):
            if isinstance(event, ReclassifyTransactionEvent):
                yield event
                continue
            summary = event

        if summary is None:
            summary = _ReclassificationSummary(
                reclassified=0,
                unchanged=len(drafts),
                failed=0,
                details=(),
            )

        for event in self._build_result_events(len(drafts), summary):
            yield event

    def _build_result_events(
        self,
        total: int,
        summary: _ReclassificationSummary | None = None,
    ) -> tuple[ReclassifyCompletedEvent, ReclassifyResultDTO]:
        """Build the terminal completion and result events."""
        if summary is None:
            summary = _ReclassificationSummary(
                reclassified=0,
                unchanged=0,
                failed=0,
                details=(),
            )

        return (
            ReclassifyCompletedEvent(
                total=total,
                reclassified=summary.reclassified,
                unchanged=summary.unchanged,
                failed=summary.failed,
            ),
            ReclassifyResultDTO(
                total_drafts=total,
                reclassified_count=summary.reclassified,
                unchanged_count=summary.unchanged,
                failed_count=summary.failed,
                details=summary.details,
            ),
        )

    async def _load_drafts(
        self,
        transaction_ids: list[UUID] | None,
        reclassify_all: bool,
        only_fallback: bool,
    ) -> list[Transaction]:
        """Load and filter draft transactions for reclassification."""
        if transaction_ids:
            all_drafts = []
            for txn_id in transaction_ids:
                txn = await self._transaction_repo.find_by_id(txn_id)
                if txn and not txn.is_posted:
                    all_drafts.append(txn)
        elif reclassify_all:
            all_drafts = await self._transaction_repo.find_draft_transactions()
        else:
            return []

        # Filter to bank-import transactions only
        drafts = [
            txn
            for txn in all_drafts
            if txn.source == TransactionSource.BANK_IMPORT
            and not txn.is_internal_transfer
        ]

        if only_fallback:
            drafts = [txn for txn in drafts if has_fallback_counter_account(txn)]

        logger.info(
            "Loaded %d draft bank-import transactions for reclassification "
            "(only_fallback=%s)",
            len(drafts),
            only_fallback,
        )
        return drafts

    def _build_ml_inputs(
        self,
        drafts: list[Transaction],
    ) -> list[_DraftAsStoredTransaction]:
        """Build ML-compatible inputs from draft transactions.

        The MLBatchClassificationService expects StoredBankTransaction objects.
        We create lightweight wrappers that provide the same interface.
        """
        return [_DraftAsStoredTransaction(txn) for txn in drafts]

    async def _stream_classifications(
        self,
        drafts: list[Transaction],
    ) -> AsyncIterator[ReclassifyProgressEvent | dict[UUID, BatchClassificationResult]]:
        """Classify drafts while yielding progress updates."""
        classifications: dict[UUID, BatchClassificationResult] = {}
        ml_inputs = self._build_ml_inputs(drafts)

        async for event in self._ml_service.classify_batch_streaming(
            stored_transactions=cast(list, ml_inputs),
            iban=_RECLASSIFY_PROGRESS_SCOPE,
            chunk_size=5,
        ):
            if isinstance(event, ClassificationProgressEvent):
                yield ReclassifyProgressEvent(
                    current=event.current,
                    total=event.total,
                )
                continue

            if isinstance(event, dict):
                classifications = event

        yield classifications

    async def _apply_classifications_streaming(
        self,
        drafts: list[Transaction],
        classifications: dict[UUID, BatchClassificationResult],
    ) -> AsyncIterator[ReclassifyTransactionEvent | _ReclassificationSummary]:
        """Apply ML classifications and yield per-transaction progress events."""
        reclassified = 0
        unchanged = 0
        failed = 0
        details: list[ReclassifiedTransactionDetail] = []

        for index, txn in enumerate(drafts, 1):
            ml_result = classifications.get(txn.id)
            if ml_result is None or ml_result.counter_account_id is None:
                unchanged += 1
                continue

            try:
                result = await self._apply_classification(txn, ml_result)
                if result is None:
                    unchanged += 1
                    continue

                reclassified += 1
                details.append(result)
                yield ReclassifyTransactionEvent(
                    transaction_id=txn.id,
                    description=txn.description[:80],
                    old_account=result.old_account_name,
                    new_account=result.new_account_name,
                    confidence=result.confidence,
                    current=index,
                    total=len(drafts),
                )
            except Exception:
                logger.exception(
                    "Failed to reclassify transaction %s",
                    txn.id,
                )
                failed += 1

        yield _ReclassificationSummary(
            reclassified=reclassified,
            unchanged=unchanged,
            failed=failed,
            details=tuple(details),
        )

    async def _apply_classification(
        self,
        txn: Transaction,
        ml_result: BatchClassificationResult,
    ) -> ReclassifiedTransactionDetail | None:
        """Apply ML classification to a draft, returning detail if changed."""
        result = await MLClassificationApplicationService.apply_to_transaction(
            txn=txn,
            ml_result=ml_result,
            account_repo=self._account_repo,
        )
        if result is None:
            return None

        await self._transaction_repo.save(txn)

        return ReclassifiedTransactionDetail(
            transaction_id=txn.id,
            old_account_number=(
                result.old_account.account_number if result.old_account else ""
            ),
            old_account_name=result.old_account.name if result.old_account else "",
            new_account_number=result.account.account_number,
            new_account_name=result.account.name,
            confidence=result.confidence,
            tier=result.tier,
        )


class _DraftAsStoredTransaction:
    """Adapter: make a Transaction look like a StoredBankTransaction.

    The MLBatchClassificationService expects StoredBankTransaction with
    .id, .transaction.booking_date, .transaction.purpose, etc.
    This adapter provides that interface from draft Transaction data.
    """

    def __init__(self, txn: Transaction):
        self.id = txn.id
        self.transaction = _DraftAsBankTransaction(txn)


class _DraftAsBankTransaction:
    """Adapter: expose Transaction fields as BankTransaction-like attributes."""

    def __init__(self, txn: Transaction):
        self.booking_date = txn.date.date() if txn.date else None
        # Use original purpose from metadata if available, otherwise description
        metadata = txn.metadata_raw
        self.purpose = metadata.get("original_purpose", txn.description) or ""
        self.amount = self._extract_amount(txn)
        self.applicant_name = txn.counterparty
        self.applicant_iban = txn.counterparty_iban

    @staticmethod
    def _extract_amount(txn: Transaction) -> Decimal:
        """Extract the original bank transaction amount.

        For bank imports, the amount is stored in the protected (asset) entry.
        Credit on asset = money out (negative), Debit on asset = money in (positive).
        """
        for entry in txn.entries:
            if txn.is_entry_protected(entry):
                if entry.is_debit():
                    return entry.debit.amount
                return -entry.credit.amount
        return txn.total_amount().amount
