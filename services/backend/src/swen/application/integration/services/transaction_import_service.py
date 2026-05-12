"""Application service for importing bank transactions into the accounting system.

This service orchestrates the import flow for a batch of pre-resolved
transactions:
- BankImportTransactionFactory: Creates accounting transactions
- TransferReconciliationService: Handles internal transfers

Responsibilities:
1. Check for duplicates (idempotency)
2. Coordinate transfer detection and reconciliation
3. Delegate transaction creation to factory
4. Track import status for audit trail

Counter-account resolution is handled upstream by
``CounterAccountBatchService`` — this service receives already-validated
``ResolvedCounterAccount`` objects.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.factories import BankImportTransactionFactory
from swen.application.integration.dtos.transaction_import_result import (
    TransactionImportResult,
)
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.accounting.value_objects import AIResolutionMetadata
from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.services import (
    BankAccountImportService,
    TransferReconciliationService,
)
from swen.domain.integration.value_objects import (
    ImportStatus,
    ResolvedCounterAccount,
)
from swen.domain.shared.time import utc_now

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.repositories import TransactionImportRepository
    from swen.domain.shared.current_user import CurrentUser


class TransactionImportService:
    """Application service for importing bank trxs into the accounting system."""

    def __init__(  # NOQA: PLR0913
        self,
        bank_account_import_service: BankAccountImportService,
        transfer_reconciliation_service: TransferReconciliationService,
        opening_balance_service: OpeningBalanceService,
        transaction_factory: BankImportTransactionFactory,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        import_repository: TransactionImportRepository,
        current_user: CurrentUser,
    ):
        self._bank_account_service = bank_account_import_service
        self._transfer_service = transfer_reconciliation_service
        self._ob_adjustment_service = opening_balance_service
        self._factory = transaction_factory
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._import_repo = import_repository
        self._user_id = current_user.user_id

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> TransactionImportService:
        bank_account_import_service = BankAccountImportService(
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
            current_user=factory.current_user,
            bank_account_repository=factory.bank_account_repository(),
        )

        ob_service = OpeningBalanceService(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            user_id=factory.current_user.user_id,
        )

        transfer_service = TransferReconciliationService(
            transaction_repository=factory.transaction_repository(),
        )

        transaction_factory = BankImportTransactionFactory(
            current_user=factory.current_user,
        )

        return cls(
            bank_account_import_service=bank_account_import_service,
            transfer_reconciliation_service=transfer_service,
            opening_balance_service=ob_service,
            transaction_factory=transaction_factory,
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            import_repository=factory.import_repository(),
            current_user=factory.current_user,
        )

    async def import_batch(
        self,
        stored_transactions: list[StoredBankTransaction],
        source_iban: str,
        resolved: dict[UUID, ResolvedCounterAccount],
        auto_post: bool = False,
    ) -> list[TransactionImportResult]:
        """Import a batch of transactions with pre-resolved counter-accounts.

        Parameters
        ----------
        stored_transactions
            Bank transactions to import.
        source_iban
            Source IBAN for asset account lookup.
        resolved
            Dict mapping ``StoredBankTransaction.id`` to the pre-validated
            ``ResolvedCounterAccount``.
        auto_post
            Whether to auto-post transactions.

        Returns
        -------
        list[TransactionImportResult]
            One result per input transaction.
        """
        results: list[TransactionImportResult] = []
        logger.debug(
            "import_batch: %d txns, %d resolved",
            len(stored_transactions),
            len(resolved),
        )
        for stored in stored_transactions:
            resolved_item = resolved[stored.id]
            result = await self._import_stored_transaction(
                stored,
                source_iban,
                resolved_item,
                auto_post=auto_post,
            )
            results.append(result)
        return results

    async def _import_stored_transaction(
        self,
        stored: StoredBankTransaction,
        source_iban: str,
        resolved_item: ResolvedCounterAccount,
        auto_post: bool = False,
    ) -> TransactionImportResult:
        """Import a single stored transaction with a resolved counter-account."""
        bank_transaction = stored.transaction

        if await self._is_already_imported(stored.id):
            return TransactionImportResult(
                bank_transaction=bank_transaction,
                status=ImportStatus.DUPLICATE,
                error_message="Transaction already imported",
            )

        import_record = TransactionImport(
            user_id=self._user_id,
            bank_transaction_id=stored.id,
            booking_date=stored.transaction.booking_date,
            status=ImportStatus.PENDING,
        )

        skip_result = await self._check_skip_conditions(bank_transaction, import_record)
        if skip_result:
            return skip_result

        try:
            return await self._process_import(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                import_record=import_record,
                resolved_item=resolved_item,
                auto_post=auto_post,
            )
        except Exception as e:
            return await self._handle_failure(bank_transaction, import_record, e)

    async def _process_import(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        import_record: TransactionImport,
        resolved_item: ResolvedCounterAccount,
        auto_post: bool,
    ) -> TransactionImportResult:
        """Process a single import.

        Uses the pre-resolved counter-account, creates accounting
        transaction, and persists atomically.
        """
        asset_account = await self._bank_account_service.get_or_create_asset_account(
            iban=source_iban,
        )

        counter_account = resolved_item.account

        # For internal asset transfers, attempt reconciliation first
        if counter_account.iban and counter_account.is_asset_account():
            result = await self._try_reconcile(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                counterparty_iban=counter_account.iban,
                asset_account=asset_account,
                import_record=import_record,
            )
            if result:
                return result

        ai_resolution = self._build_ai_resolution_metadata(resolved_item)

        accounting_tx = self._factory.create(
            bank_transaction=bank_transaction,
            asset_account=asset_account,
            counter_account=counter_account,
            source_iban=source_iban,
            is_internal_transfer=counter_account.iban is not None,
            ai_resolution=ai_resolution,
        )

        if auto_post:
            accounting_tx.post()

        ob_adjustment = await self._ob_adjustment_service.build_adjustment_transaction(
            counterparty_account=counter_account,
            bank_transaction=bank_transaction,
            source_iban=source_iban,
        )

        import_record.mark_as_imported(accounting_tx.id)
        await self._import_repo.save_complete_import(
            import_record=import_record,
            accounting_tx=accounting_tx,
            ob_adjustment=ob_adjustment,
        )

        return TransactionImportResult(
            bank_transaction=bank_transaction,
            status=ImportStatus.SUCCESS,
            accounting_transaction=accounting_tx,
        )

    async def _check_skip_conditions(
        self,
        bank_transaction: BankTransaction,
        import_record: TransactionImport,
    ) -> TransactionImportResult | None:
        skip_reason = None

        if bank_transaction.amount == 0:
            skip_reason = "Skipping zero-amount bank transaction"
        elif bank_transaction.currency != "EUR":
            skip_reason = f"Unsupported currency: {bank_transaction.currency}"

        if skip_reason:
            import_record.mark_as_skipped(skip_reason)
            await self._import_repo.save(import_record)
            return TransactionImportResult(
                bank_transaction=bank_transaction,
                status=ImportStatus.SKIPPED,
                error_message=skip_reason,
            )

        return None

    async def _is_already_imported(self, bank_transaction_id) -> bool:
        existing = await self._import_repo.find_by_bank_transaction_id(
            bank_transaction_id,
        )
        return existing is not None and existing.status == ImportStatus.SUCCESS

    async def _try_reconcile(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        counterparty_iban: str,
        asset_account: Account,
        import_record: TransactionImport,
    ) -> TransactionImportResult | None:
        existing = await self._transfer_service.find_matching_transfer(
            bank_transaction=bank_transaction,
            source_iban=source_iban,
            counterparty_iban=counterparty_iban,
        )

        if not existing:
            return None

        if existing.is_internal_transfer:
            import_record.mark_as_imported(existing.id)
            await self._import_repo.save(import_record)
            logger.info(
                "Transfer already imported from other account: %s",
                existing.id,
            )
            return TransactionImportResult(
                bank_transaction=bank_transaction,
                status=ImportStatus.DUPLICATE,
                accounting_transaction=existing,
                error_message="Transfer already imported from other account",
            )

        await self._import_repo.mark_reconciled_as_internal_transfer(
            import_record=import_record,
            existing_transaction=existing,
            new_asset_account=asset_account,
            source_iban=counterparty_iban,
            counterparty_iban=source_iban,
        )
        logger.info(
            "Reconciled existing transaction %s as internal transfer",
            existing.id,
        )
        return TransactionImportResult(
            bank_transaction=bank_transaction,
            status=ImportStatus.SUCCESS,
            accounting_transaction=existing,
            error_message="Reconciled existing transaction as internal transfer",
            was_reconciled=True,
        )

    async def _handle_failure(
        self,
        bank_transaction: BankTransaction,
        import_record: TransactionImport,
        error: Exception,
    ) -> TransactionImportResult:
        error_msg = f"Import failed: {error!s}"
        import_record.mark_as_failed(error_msg)
        await self._import_repo.save(import_record)

        return TransactionImportResult(
            bank_transaction=bank_transaction,
            status=ImportStatus.FAILED,
            error_message=error_msg,
        )

    def _build_ai_resolution_metadata(
        self,
        resolved_item: ResolvedCounterAccount,
    ) -> AIResolutionMetadata | None:
        """Translate integration resolution into accounting AI metadata.

        This is the boundary translation: the import service knows both the
        integration VO (``ResolvedCounterAccount``) and the accounting VO
        (``AIResolutionMetadata``). The factory only receives the latter.
        """
        if resolved_item.confidence is None:
            return None

        return AIResolutionMetadata(
            suggested_counter_account_id=str(resolved_item.account.id),
            suggested_counter_account_name=resolved_item.account.name,
            confidence=resolved_item.confidence,
            reasoning=None,
            model="swen-ml-batch",
            resolved_at=utc_now(),
            suggestion_accepted=True,
        )

    async def get_import_statistics(self, iban: str | None = None) -> dict[str, int]:
        status_counts = await self._import_repo.count_by_status(iban)

        def _count(status: ImportStatus) -> int:
            return status_counts.get(status.value, 0)

        stats = {
            "success": _count(ImportStatus.SUCCESS),
            "failed": _count(ImportStatus.FAILED),
            "pending": _count(ImportStatus.PENDING),
            "duplicate": _count(ImportStatus.DUPLICATE),
            "skipped": _count(ImportStatus.SKIPPED),
        }
        stats["total"] = sum(stats.values())
        return stats

    async def reconcile_transfers_for_account(
        self,
        iban: str,
        asset_account: Account,
    ) -> int:
        return await self._transfer_service.reconcile_for_new_account(
            iban=iban,
            asset_account=asset_account,
        )

    @staticmethod
    def compute_stats(
        import_results: list[TransactionImportResult],
    ) -> tuple[int, int, int]:
        imported = skipped = failed = 0
        for result in import_results:
            if result.status == ImportStatus.SUCCESS:
                imported += 1
            elif result.status in (ImportStatus.DUPLICATE, ImportStatus.SKIPPED):
                skipped += 1
            elif result.status == ImportStatus.FAILED:
                failed += 1
        return imported, skipped, failed
