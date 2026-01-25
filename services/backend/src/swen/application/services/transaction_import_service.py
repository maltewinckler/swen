"""Application service for importing bank transactions into the accounting system.

This service orchestrates the import flow using:
- BankImportTransactionFactory: Creates accounting transactions
- TransferReconciliationService: Handles internal transfers
- CounterAccountResolutionService: Resolves counter-accounts

Responsibilities:
1. Check for duplicates (idempotency)
2. Coordinate transfer detection and reconciliation
3. Resolve counter-accounts
4. Delegate transaction creation to factory
5. Track import status for audit trail
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Awaitable, Callable, Optional
from uuid import UUID

from swen.application.factories import BankImportTransactionFactory
from swen.application.queries.integration import OpeningBalanceQuery
from swen.application.services.bank_account_import_service import (
    BankAccountImportService,
)
from swen.application.services.opening_balance_adjustment_service import (
    OpeningBalanceAdjustmentService,
)
from swen.application.services.transfer_reconciliation_service import (
    TransferContext,
    TransferReconciliationService,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.services import CounterAccountResolutionService
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    ImportStatus,
    ResolutionResult,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from swen.application.factories import RepositoryFactory
    from swen.application.ports.identity import CurrentUser
    from swen.application.services.ml_batch_classification_service import (
        BatchClassificationResult,
    )
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.repositories import TransactionImportRepository


class TransactionImportResult:
    """Result of a transaction import attempt."""

    def __init__(
        self,
        bank_transaction: BankTransaction,
        status: ImportStatus,
        accounting_transaction: Transaction | None = None,
        error_message: str | None = None,
        was_reconciled: bool = False,
    ):
        self.bank_transaction = bank_transaction
        self.status = status
        self.accounting_transaction = accounting_transaction
        self.error_message = error_message
        self.was_reconciled = was_reconciled

    @property
    def is_success(self) -> bool:
        return self.status == ImportStatus.SUCCESS

    @property
    def is_duplicate(self) -> bool:
        return self.status == ImportStatus.DUPLICATE

    @property
    def is_failed(self) -> bool:
        return self.status == ImportStatus.FAILED

    @property
    def is_reconciled(self) -> bool:
        return self.was_reconciled


class TransactionImportService:
    """Application service for importing bank trxs into the accounting system."""

    def __init__(  # NOQA: PLR0913
        self,
        bank_account_import_service: BankAccountImportService,
        counter_account_resolution_service: CounterAccountResolutionService,
        transfer_reconciliation_service: TransferReconciliationService,
        opening_balance_adjustment_service: OpeningBalanceAdjustmentService,
        transaction_factory: BankImportTransactionFactory,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        import_repository: TransactionImportRepository,
        current_user: CurrentUser,
        db_session: Optional[AsyncSession] = None,
    ):
        self._bank_account_service = bank_account_import_service
        self._counter_account_service = counter_account_resolution_service
        self._transfer_service = transfer_reconciliation_service
        self._ob_adjustment_service = opening_balance_adjustment_service
        self._factory = transaction_factory
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._import_repo = import_repository
        self._user_id = current_user.user_id
        self._db_session = db_session

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> TransactionImportService:
        counter_account_service = CounterAccountResolutionService(
            rule_repository=factory.counter_account_rule_repository(),
            user_id=factory.current_user.user_id,
        )

        ob_query = OpeningBalanceQuery.from_factory(factory)

        transfer_service = TransferReconciliationService(
            transaction_repository=factory.transaction_repository(),
            mapping_repository=factory.account_mapping_repository(),
            account_repository=factory.account_repository(),
            opening_balance_query=ob_query,
        )

        transaction_factory = BankImportTransactionFactory(
            current_user=factory.current_user,
        )

        ob_adjustment_service = OpeningBalanceAdjustmentService(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            opening_balance_query=ob_query,
            current_user=factory.current_user,
        )

        return cls(
            bank_account_import_service=BankAccountImportService.from_factory(factory),
            counter_account_resolution_service=counter_account_service,
            transfer_reconciliation_service=transfer_service,
            opening_balance_adjustment_service=ob_adjustment_service,
            transaction_factory=transaction_factory,
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            import_repository=factory.import_repository(),
            current_user=factory.current_user,
            db_session=factory.session,
        )

    async def _run_atomically(self, fn: Callable[[], Awaitable[None]]):
        if self._db_session is None:
            await fn()
            return

        # If the caller already manages a transaction, dont start a nested one
        # (e.g API layer might wrap a whole sync in a transaction)
        if self._db_session.in_transaction and self._db_session.in_transaction():
            await fn()
            return

        async with self._db_session.begin():
            await fn()

    async def import_from_stored_transactions(
        self,
        stored_transactions: list[StoredBankTransaction],
        source_iban: str,
        auto_post: bool = False,
    ) -> list[TransactionImportResult]:
        results = []
        for stored in stored_transactions:
            result = await self._import_stored_transaction(
                stored,
                source_iban,
                auto_post=auto_post,
            )
            results.append(result)
        return results

    async def import_from_stored_transactions_streaming(
        self,
        stored_transactions: list[StoredBankTransaction],
        source_iban: str,
        auto_post: bool = False,
    ):
        total = len(stored_transactions)
        for i, stored in enumerate(stored_transactions):
            result = await self._import_stored_transaction(
                stored,
                source_iban,
                auto_post=auto_post,
            )
            yield (i + 1, total, result)

    async def import_with_preclassified(
        self,
        stored_transactions: list[StoredBankTransaction],
        source_iban: str,
        preclassified: dict[UUID, BatchClassificationResult],
        auto_post: bool = False,
    ) -> list[TransactionImportResult]:
        """Import transactions using pre-classified ML results.

        Parameters
        ----------
        stored_transactions
            Bank transactions to import
        source_iban
            Source IBAN for asset account lookup
        preclassified
            Dict mapping bank_transaction_id -> BatchClassificationResult
        auto_post
            Whether to auto-post transactions

        Returns
        -------
        list[TransactionImportResult]
            Import results for each transaction
        """
        results = []
        for stored in stored_transactions:
            ml_result = preclassified.get(stored.id)
            result = await self._import_stored_transaction_preclassified(
                stored,
                source_iban,
                ml_result,
                auto_post=auto_post,
            )
            results.append(result)
        return results

    async def import_with_preclassified_streaming(
        self,
        stored_transactions: list[StoredBankTransaction],
        source_iban: str,
        preclassified: dict[UUID, BatchClassificationResult],
        auto_post: bool = False,
    ):
        """Import transactions using pre-classified ML results (streaming).

        Parameters
        ----------
        stored_transactions
            Bank transactions to import
        source_iban
            Source IBAN for asset account lookup
        preclassified
            Dict mapping bank_transaction_id -> BatchClassificationResult
        auto_post
            Whether to auto-post transactions

        Yields
        ------
        tuple[int, int, TransactionImportResult]
            (current, total, result) for each transaction
        """
        total = len(stored_transactions)
        logger.debug(
            "import_with_preclassified_streaming: %d txns, %d preclassified results",
            total,
            len(preclassified),
        )
        for i, stored in enumerate(stored_transactions):
            ml_result = preclassified.get(stored.id)
            if ml_result is None and len(preclassified) > 0:
                logger.warning(
                    "No ML result for stored.id=%s. Preclassified keys: %s",
                    stored.id,
                    list(preclassified.keys())[:5],
                )
            result = await self._import_stored_transaction_preclassified(
                stored,
                source_iban,
                ml_result,
                auto_post=auto_post,
            )
            yield (i + 1, total, result)

    async def _import_stored_transaction_preclassified(
        self,
        stored: StoredBankTransaction,
        source_iban: str,
        ml_result: BatchClassificationResult | None,
        auto_post: bool = False,
    ) -> TransactionImportResult:
        """Import a transaction using pre-classified ML result."""
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
            status=ImportStatus.PENDING,
        )

        skip_result = await self._check_skip_conditions(bank_transaction, import_record)
        if skip_result:
            return skip_result

        try:
            return await self._process_import_preclassified(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                import_record=import_record,
                ml_result=ml_result,
                auto_post=auto_post,
            )
        except Exception as e:
            return await self._handle_failure(bank_transaction, import_record, e)

    async def _process_import_preclassified(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        import_record: TransactionImport,
        ml_result: BatchClassificationResult | None,
        auto_post: bool,
    ) -> TransactionImportResult:
        """Process import using pre-classified ML result."""
        asset_account = await self._bank_account_service.get_or_create_asset_account(
            iban=source_iban,
        )

        transfer_context = await self._transfer_service.detect_transfer(
            bank_transaction,
        )

        if transfer_context.can_reconcile:
            result = await self._try_reconcile(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                transfer_context=transfer_context,
                asset_account=asset_account,
                import_record=import_record,
            )
            if result:
                return result

        # Use pre-classified result instead of calling AI
        counter_account, resolution_result = await self._resolve_with_preclassified(
            bank_transaction=bank_transaction,
            transfer_context=transfer_context,
            ml_result=ml_result,
        )

        accounting_tx = self._factory.create(
            bank_transaction=bank_transaction,
            asset_account=asset_account,
            counter_account=counter_account,
            source_iban=source_iban,
            is_internal_transfer=transfer_context.is_internal_transfer,
            resolution_result=resolution_result,
            merchant=ml_result.merchant if ml_result else None,
            is_recurring=ml_result.is_recurring if ml_result else False,
            recurring_pattern=ml_result.recurring_pattern if ml_result else None,
        )

        if auto_post:
            accounting_tx.post()

        await self._persist_with_ob_adjustment(
            accounting_tx=accounting_tx,
            bank_transaction=bank_transaction,
            source_iban=source_iban,
            transfer_context=transfer_context,
            import_record=import_record,
        )

        return TransactionImportResult(
            bank_transaction=bank_transaction,
            status=ImportStatus.SUCCESS,
            accounting_transaction=accounting_tx,
        )

    async def _resolve_with_preclassified(
        self,
        bank_transaction: BankTransaction,
        transfer_context: TransferContext,
        ml_result: BatchClassificationResult | None,
    ) -> tuple["Account", ResolutionResult | None]:
        """Resolve counter account using pre-classified ML result."""
        # Debug: log the incoming ml_result
        if ml_result:
            logger.debug(
                "Resolving with ML: tx_id=%s, account_id=%s, account_number=%s, "
                "tier=%s, conf=%.2f",
                ml_result.transaction_id,
                ml_result.counter_account_id,
                ml_result.counter_account_number,
                ml_result.tier,
                ml_result.confidence,
            )
        else:
            logger.debug(
                "Resolving without ML result for: %s",
                bank_transaction.applicant_name or bank_transaction.purpose[:30],
            )

        # Internal transfers use the counterparty account
        if (
            transfer_context.is_internal_transfer
            and transfer_context.counterparty_account
        ):
            return transfer_context.counterparty_account, None

        # If we have a valid ML result, use it
        if ml_result and ml_result.counter_account_id:
            account = await self._account_repo.find_by_id(ml_result.counter_account_id)
            if account:
                ai_result = AICounterAccountResult(
                    counter_account_id=ml_result.counter_account_id,
                    confidence=ml_result.confidence,
                    tier=ml_result.tier,
                )
                logger.debug(
                    "Using ML classification: account=%s (%s), tier=%s, conf=%.2f",
                    account.account_number,
                    account.name,
                    ml_result.tier,
                    ml_result.confidence,
                )
                return account, ResolutionResult(
                    account=account,
                    ai_result=ai_result,
                    source="ai",
                )

            logger.warning(
                "ML result has account_id=%s but account not found in repository",
                ml_result.counter_account_id,
            )
        elif ml_result:
            logger.debug(
                "ML result has no account_id (tier=%s, conf=%.2f)",
                ml_result.tier,
                ml_result.confidence,
            )

        # Fallback to default account
        fallback = await self._counter_account_service.get_fallback_account(
            is_expense=bank_transaction.is_debit(),
            account_repository=self._account_repo,
        )
        return fallback, ResolutionResult(account=fallback, source="fallback")

    async def _import_stored_transaction(
        self,
        stored: StoredBankTransaction,
        source_iban: str,
        auto_post: bool = False,
    ) -> TransactionImportResult:
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
                auto_post=auto_post,
            )
        except Exception as e:
            return await self._handle_failure(bank_transaction, import_record, e)

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

    async def _process_import(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        import_record: TransactionImport,
        auto_post: bool,
    ) -> TransactionImportResult:
        asset_account = await self._bank_account_service.get_or_create_asset_account(
            iban=source_iban,
        )

        transfer_context = await self._transfer_service.detect_transfer(
            bank_transaction,
        )

        if transfer_context.can_reconcile:
            result = await self._try_reconcile(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                transfer_context=transfer_context,
                asset_account=asset_account,
                import_record=import_record,
            )
            if result:
                return result

        counter_account, resolution_result = await self._resolve_counter_account(
            bank_transaction=bank_transaction,
            transfer_context=transfer_context,
        )

        accounting_tx = self._factory.create(
            bank_transaction=bank_transaction,
            asset_account=asset_account,
            counter_account=counter_account,
            source_iban=source_iban,
            is_internal_transfer=transfer_context.is_internal_transfer,
            resolution_result=resolution_result,
        )

        if auto_post:
            accounting_tx.post()

        await self._persist_with_ob_adjustment(
            accounting_tx=accounting_tx,
            bank_transaction=bank_transaction,
            source_iban=source_iban,
            transfer_context=transfer_context,
            import_record=import_record,
        )

        return TransactionImportResult(
            bank_transaction=bank_transaction,
            status=ImportStatus.SUCCESS,
            accounting_transaction=accounting_tx,
        )

    async def _persist_with_ob_adjustment(
        self,
        accounting_tx: Transaction,
        bank_transaction: BankTransaction,
        source_iban: str,
        transfer_context: TransferContext,
        import_record: TransactionImport,
    ) -> None:
        needs_ob_adjustment = (
            transfer_context.is_internal_transfer
            and transfer_context.counterparty_account is not None
            and transfer_context.is_pre_opening_balance(bank_transaction.booking_date)
        )

        transfer_hash = None
        if bank_transaction.applicant_iban:
            transfer_hash = bank_transaction.compute_transfer_identity_hash(
                source_iban,
                bank_transaction.applicant_iban,
            )

        async def _persist() -> None:
            await self._transaction_repo.save(accounting_tx)
            import_record.mark_as_imported(accounting_tx.id)
            await self._import_repo.save(import_record)

            if (
                needs_ob_adjustment
                and transfer_context.counterparty_account is not None
                and transfer_context.counterparty_iban is not None
            ):
                await self._ob_adjustment_service.create_adjustment_if_needed(
                    counterparty_account=transfer_context.counterparty_account,
                    counterparty_iban=transfer_context.counterparty_iban,
                    transfer_amount=abs(bank_transaction.amount),
                    transfer_date=bank_transaction.booking_date,
                    # Money OUT from source = INCOMING to counterparty
                    is_incoming_to_counterparty=bank_transaction.is_debit(),
                    transfer_hash=transfer_hash,
                )

        await self._run_atomically(_persist)

    async def _is_already_imported(self, bank_transaction_id) -> bool:
        existing = await self._import_repo.find_by_bank_transaction_id(
            bank_transaction_id,
        )
        return existing is not None and existing.status == ImportStatus.SUCCESS

    async def _try_reconcile(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        transfer_context: TransferContext,
        asset_account: Account,
        import_record: TransactionImport,
    ) -> TransactionImportResult | None:
        counterparty_iban = transfer_context.counterparty_iban
        if not counterparty_iban:
            return None

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

        async def _persist_reconciliation() -> None:
            await self._transfer_service.convert_to_internal_transfer(
                transaction=existing,
                new_asset_account=asset_account,
                counterparty_iban=source_iban,
                source_iban=counterparty_iban,
            )
            import_record.mark_as_imported(existing.id)
            await self._import_repo.save(import_record)

        await self._run_atomically(_persist_reconciliation)

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

    async def _resolve_counter_account(
        self,
        bank_transaction: BankTransaction,
        transfer_context: TransferContext,
    ) -> tuple["Account", ResolutionResult | None]:
        if (
            transfer_context.is_internal_transfer
            and transfer_context.counterparty_account
        ):
            return transfer_context.counterparty_account, None

        resolution_result = (
            await self._counter_account_service.resolve_counter_account_with_details(
                bank_transaction=bank_transaction,
                account_repository=self._account_repo,
            )
        )

        if resolution_result.account:
            return resolution_result.account, resolution_result

        fallback = await self._counter_account_service.get_fallback_account(
            is_expense=bank_transaction.is_debit(),
            account_repository=self._account_repo,
        )
        return fallback, resolution_result

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
