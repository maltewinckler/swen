"""Sync result aggregator.

Consolidates per-account statistics and success/error/warning message
building previously inlined on the deleted ``TransactionSyncCommand``,
producing the final :class:`SyncResult` DTO emitted by
``BankAccountSyncService``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from swen.application.dtos.integration.sync_result import SyncResult
from swen.domain.integration.value_objects import ImportStatus

if TYPE_CHECKING:
    from datetime import datetime

    from swen.application.dtos.integration.sync_period import SyncPeriod
    from swen.application.services.transaction_import_service import (
        TransactionImportResult,
    )
    from swen.domain.accounting.services.opening_balance.service import (
        OpeningBalanceOutcome,
    )
    from swen.domain.banking.value_objects import BankTransaction


_MAX_SAMPLE_ERRORS = 3


class SyncResultAggregator:
    """Build per-account :class:`SyncResult` DTOs from raw sync inputs."""

    @staticmethod
    def build(  # noqa: PLR0913
        synced_at: datetime,
        iban: str,
        period: SyncPeriod,
        bank_transactions: list[BankTransaction],
        import_results: list[TransactionImportResult],
        opening_balance: OpeningBalanceOutcome,
    ) -> SyncResult:
        """Aggregate per-account stats and messages into a :class:`SyncResult`.

        Assumes ``import_results`` items expose an :class:`ImportStatus` enum on
        ``status``; no string coercion is performed.
        """
        counts = SyncResultAggregator._count_import_results(import_results)
        messages = SyncResultAggregator._build_result_messages(
            counts,
            bank_transactions,
        )

        return SyncResult(
            success=messages["success"],
            synced_at=synced_at,
            iban=iban,
            start_date=period.start_date,
            end_date=period.end_date,
            transactions_fetched=len(bank_transactions),
            transactions_imported=counts["imported"],
            transactions_skipped=counts["skipped"],
            transactions_failed=counts["failed"],
            transactions_reconciled=counts["reconciled"],
            error_message=messages["error_message"],
            warning_message=messages["warning_message"],
            opening_balance_created=opening_balance.created,
            opening_balance_amount=opening_balance.amount,
        )

    @staticmethod
    def _count_import_results(
        import_results: list[TransactionImportResult],
    ) -> dict:
        imported = 0
        skipped = 0
        failed = 0
        reconciled = 0
        error_details: list[str] = []

        for result in import_results:
            status = result.status

            if status == ImportStatus.SUCCESS:
                imported += 1
                if result.was_reconciled:
                    reconciled += 1
            elif status in (ImportStatus.DUPLICATE, ImportStatus.SKIPPED):
                skipped += 1
            elif status == ImportStatus.FAILED:
                failed += 1
                if result.error_message:
                    error_details.append(result.error_message)

        return {
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
            "reconciled": reconciled,
            "error_details": error_details,
        }

    @staticmethod
    def _build_result_messages(
        counts: dict,
        bank_transactions: list[BankTransaction],
    ) -> dict:
        failed = counts["failed"]
        imported = counts["imported"]
        skipped = counts["skipped"]
        reconciled = counts["reconciled"]
        error_details = counts["error_details"]

        has_failures = failed > 0
        has_positive_outcome = imported > 0 or skipped > 0 or not bank_transactions
        success_flag = not has_failures or has_positive_outcome

        warning_message = SyncResultAggregator._build_warning_message(
            has_failures=has_failures,
            success_flag=success_flag,
            failed=failed,
            error_details=error_details,
            reconciled=reconciled,
        )
        error_message = SyncResultAggregator._build_error_message(
            has_failures=has_failures,
            success_flag=success_flag,
            failed=failed,
            error_details=error_details,
        )

        return {
            "success": success_flag,
            "warning_message": warning_message,
            "error_message": error_message,
        }

    @staticmethod
    def _build_warning_message(
        *,
        has_failures: bool,
        success_flag: bool,
        failed: int,
        error_details: list[str],
        reconciled: int,
    ) -> Optional[str]:
        warning_message: Optional[str] = None

        if has_failures and success_flag:
            warning_message = SyncResultAggregator._format_failure_message(
                failed,
                error_details,
            )

        if reconciled > 0:
            reconcile_msg = (
                f"Reconciled {reconciled} internal transfer"
                f"{'s' if reconciled != 1 else ''} with existing transactions"
            )
            warning_message = (
                f"{warning_message}. {reconcile_msg}"
                if warning_message
                else reconcile_msg
            )

        return warning_message

    @staticmethod
    def _build_error_message(
        *,
        has_failures: bool,
        success_flag: bool,
        failed: int,
        error_details: list[str],
    ) -> Optional[str]:
        if has_failures and not success_flag:
            return SyncResultAggregator._format_failure_message(
                failed,
                error_details,
            )
        return None

    @staticmethod
    def _format_failure_message(
        failed_count: int,
        error_details: list[str],
    ) -> str:
        failure_msg = (
            f"{failed_count} transaction{'s' if failed_count != 1 else ''} "
            "failed to import"
        )
        if error_details:
            sample_errors = error_details[:_MAX_SAMPLE_ERRORS]
            failure_msg += ": " + "; ".join(sample_errors)
            if len(error_details) > _MAX_SAMPLE_ERRORS:
                failure_msg += f" (and {len(error_details) - _MAX_SAMPLE_ERRORS} more)"
        return failure_msg
