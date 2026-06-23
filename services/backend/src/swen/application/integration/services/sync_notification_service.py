"""Stateful notification service for the sync pipeline.

Wraps the ``SyncEventPublisher`` port and holds per-sync-process state
(current account context, running totals). All event construction is
centralised here so that the command and per-IBAN service only call
thin ``emit_*()`` methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.events import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    BatchSyncCompletedEvent,
    BatchSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
    ErrorCode,
    SyncResultEvent,
)

if TYPE_CHECKING:
    from swen.application.ports.integration.sync_event_publisher import (
        SyncEventPublisher,
    )


class SyncNotificationService:
    """Publish sync progress events with internally tracked state."""

    def __init__(self, publisher: SyncEventPublisher) -> None:
        self._publisher = publisher

        # Batch-level state
        self._total_accounts: int = 0
        self._accounts_synced: int = 0
        self._total_imported: int = 0  # imported trx in whole process
        self._total_skipped: int = 0  # skipped trx in whole process
        self._total_failed: int = 0  # failed trx in whole process

        # Per-account state
        self._account_index: int = 0
        self._iban_in_progress: str = ""
        self._account_name_in_progress: str = ""

    async def update_import_counts(self, imported: int, skipped: int, failed: int):
        self._total_imported += imported
        self._total_skipped += skipped
        self._total_failed += failed

    async def emit_batch_sync_started_event(self, total_accounts: int):
        self._total_accounts = total_accounts
        await self._publisher.publish(
            BatchSyncStartedEvent(total_accounts=total_accounts)
        )

    async def emit_batch_sync_completed_event(self):
        await self._publisher.publish(
            BatchSyncCompletedEvent(
                total_imported=self._total_imported,
                total_skipped=self._total_skipped,
                total_failed=self._total_failed,
                accounts_synced=self._accounts_synced,
            )
        )

    async def emit_sync_result_event(self):
        success = self._total_failed == 0 or self._total_imported > 0
        await self._publisher.publish(
            SyncResultEvent(
                success=success,
                total_imported=self._total_imported,
                total_skipped=self._total_skipped,
                total_failed=self._total_failed,
                accounts_synced=self._accounts_synced,
            )
        )

    async def emit_account_sync_started_event(
        self,
        iban: str,
        account_name: str,
    ):
        self._account_index += 1
        self._iban_in_progress = iban
        self._account_name_in_progress = account_name
        await self._publisher.publish(
            AccountSyncStartedEvent(
                iban=iban,
                account_name=account_name,
                account_index=self._account_index,
                total_accounts=self._total_accounts,
            )
        )

    async def emit_account_sync_completed_event(
        self,
        imported: int,
        skipped: int,
        failed: int,
    ):
        await self.update_import_counts(imported, skipped, failed)
        self._accounts_synced += 1
        await self._publisher.publish(
            AccountSyncCompletedEvent(
                iban=self._iban_in_progress,
                imported=imported,
                skipped=skipped,
                failed=failed,
            )
        )

    async def emit_account_sync_failed_event(
        self,
        code: ErrorCode,
        error_key: str,
    ):
        await self._publisher.publish(
            AccountSyncFailedEvent(
                iban=self._iban_in_progress,
                code=code,
                error_key=error_key,
            )
        )

    async def emit_account_sync_fetched_event(
        self,
        transactions_fetched: int,
        new_transactions: int,
    ):
        await self._publisher.publish(
            AccountSyncFetchedEvent(
                iban=self._iban_in_progress,
                transactions_fetched=transactions_fetched,
                new_transactions=new_transactions,
            )
        )

    async def emit_classification_started_event(self):
        await self._publisher.publish(
            ClassificationStartedEvent(iban=self._iban_in_progress)
        )

    async def emit_classification_progress_event(
        self,
        current: int,
        total: int,
    ):
        await self._publisher.publish(
            ClassificationProgressEvent(
                iban=self._iban_in_progress,
                current=current,
                total=total,
            )
        )

    async def emit_classification_completed_event(
        self,
        total: int,
        processing_time_ms: int,
    ):
        await self._publisher.publish(
            ClassificationCompletedEvent(
                iban=self._iban_in_progress,
                total=total,
                recurring_detected=0,
                merchants_extracted=0,
                processing_time_ms=processing_time_ms,
            )
        )

    async def close(self) -> None:
        await self._publisher.close()
