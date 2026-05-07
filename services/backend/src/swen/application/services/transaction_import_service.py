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
from datetime import datetime, time, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.factories import BankImportTransactionFactory
from swen.application.services.ml_classification_application_service import (
    MLClassificationApplicationService,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.accounting.services.opening_balance.calculator import (
    OpeningBalanceCalculator,
)
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.services import (
    BankAccountImportService,
    CounterAccountResolutionService,
    TransferContext,
    TransferReconciliationService,
)
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    ImportStatus,
    ResolutionResult,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.services.ml_batch_classification_service import (
        BatchClassificationResult,
    )
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.repositories import TransactionImportRepository
    from swen.domain.shared.current_user import CurrentUser


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
        opening_balance_service: OpeningBalanceService,
        transaction_factory: BankImportTransactionFactory,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        import_repository: TransactionImportRepository,
        current_user: CurrentUser,
    ):
        self._bank_account_service = bank_account_import_service
        self._counter_account_service = counter_account_resolution_service
        self._transfer_service = transfer_reconciliation_service
        self._ob_adjustment_service = opening_balance_service
        self._factory = transaction_factory
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._import_repo = import_repository
        self._user_id = current_user.user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> TransactionImportService:
        counter_account_service = CounterAccountResolutionService(
            rule_repository=factory.counter_account_rule_repository(),
            user_id=factory.current_user.user_id,
        )

        ob_service = OpeningBalanceService(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            user_id=factory.current_user.user_id,
        )

        transfer_service = TransferReconciliationService(
            transaction_repository=factory.transaction_repository(),
            mapping_repository=factory.account_mapping_repository(),
            account_repository=factory.account_repository(),
            opening_balance_query=ob_service,
        )

        transaction_factory = BankImportTransactionFactory(
            current_user=factory.current_user,
        )

        return cls(
            bank_account_import_service=BankAccountImportService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                current_user=factory.current_user,
            ),
            counter_account_resolution_service=counter_account_service,
            transfer_reconciliation_service=transfer_service,
            opening_balance_service=ob_service,
            transaction_factory=transaction_factory,
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            import_repository=factory.import_repository(),
            current_user=factory.current_user,
        )

    async def import_streaming(
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
            Dict mapping bank_transaction_id -> BatchClassificationResult.
            When empty, the service still works (no ML results for counter-account
            resolution).
        auto_post
            Whether to auto-post transactions

        Yields
        ------
        tuple[int, int, TransactionImportResult]
            (current, total, result) for each transaction
        """
        total = len(stored_transactions)
        logger.debug(
            "import_streaming: %d txns, %d preclassified results",
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
            result = await self._import_stored_transaction(
                stored,
                source_iban,
                ml_result,
                auto_post=auto_post,
            )
            yield (i + 1, total, result)

    async def _import_stored_transaction(
        self,
        stored: StoredBankTransaction,
        source_iban: str,
        ml_result: BatchClassificationResult | None,
        auto_post: bool = False,
    ) -> TransactionImportResult:
        """Import a single stored transaction with ML classification result."""
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
                ml_result=ml_result,
                auto_post=auto_post,
            )
        except Exception as e:
            return await self._handle_failure(bank_transaction, import_record, e)

    async def _process_import(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        import_record: TransactionImport,
        ml_result: BatchClassificationResult | None,
        auto_post: bool,
    ) -> TransactionImportResult:
        """Process a single import.

        Resolves counter-account, creates accounting transaction, and persists
        atomically.
        """
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
        # Internal transfers use the counterparty account
        if (
            transfer_context.is_internal_transfer
            and transfer_context.counterparty_account
        ):
            return transfer_context.counterparty_account, None

        # If we have a valid ML result with an account, try to use it
        if ml_result and ml_result.counter_account_id:
            logger.debug(
                "Resolving with ML: tx_id=%s, account_id=%s, account_number=%s, "
                "tier=%s, conf=%.2f",
                ml_result.transaction_id,
                ml_result.counter_account_id,
                ml_result.counter_account_number,
                ml_result.tier,
                ml_result.confidence,
            )
            is_money_outflow = bank_transaction.is_debit()
            account = await MLClassificationApplicationService.resolve_classification(
                ml_result=ml_result,
                is_money_outflow=is_money_outflow,
                account_repo=self._account_repo,
            )
            if account is not None:
                logger.debug(
                    "Using ML classification: account=%s (%s), tier=%s, conf=%.2f",
                    account.account_number,
                    account.name,
                    ml_result.tier,
                    ml_result.confidence,
                )
                return account, ResolutionResult(
                    account=account,
                    ai_result=AICounterAccountResult(
                        counter_account_id=ml_result.counter_account_id,
                        confidence=ml_result.confidence,
                        tier=ml_result.tier,
                    ),
                    source="ai",
                )

        # Fallback to default account
        fallback = await self._counter_account_service.get_fallback_account(
            is_expense=bank_transaction.is_debit(),
            account_repository=self._account_repo,
        )
        return fallback, ResolutionResult(account=fallback, source="fallback")

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

        ob_adjustment: Transaction | None = None
        if (
            needs_ob_adjustment
            and transfer_context.counterparty_account is not None
            and transfer_context.counterparty_iban is not None
        ):
            ob_adjustment = await self._build_ob_adjustment(
                bank_transaction=bank_transaction,
                source_iban=source_iban,
                transfer_context=transfer_context,
            )

        import_record.mark_as_imported(accounting_tx.id)

        await self._import_repo.save_complete_import(
            import_record=import_record,
            accounting_tx=accounting_tx,
            ob_adjustment=ob_adjustment,
        )

    async def _build_ob_adjustment(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        transfer_context: TransferContext,
    ) -> Transaction | None:
        """Build an OB adjustment Transaction without persisting it.

        Returns the adjustment Transaction or None if no adjustment is needed.
        The caller is responsible for passing it to save_complete_import for
        atomic persistence.
        """
        counterparty_account = transfer_context.counterparty_account
        counterparty_iban = transfer_context.counterparty_iban
        if counterparty_account is None or counterparty_iban is None:
            return None

        transfer_hash = None
        if bank_transaction.applicant_iban:
            transfer_hash = bank_transaction.compute_transfer_identity_hash(
                source_iban,
                bank_transaction.applicant_iban,
            )

        if transfer_hash:
            already_exists = (
                await self._ob_adjustment_service.adjustment_exists_for_transfer(
                    iban=counterparty_iban,
                    transfer_hash=transfer_hash,
                )
            )
            if already_exists:
                return None

        equity_account = await self._account_repo.find_by_account_number(
            WellKnownAccounts.OPENING_BALANCE_EQUITY,
        )
        if not equity_account:
            return None

        calculator = OpeningBalanceCalculator()
        transfer_amount = abs(bank_transaction.amount)
        is_incoming_to_counterparty = bank_transaction.is_debit()
        adjustment_amount = (
            transfer_amount if is_incoming_to_counterparty else -transfer_amount
        )

        adjustment_datetime = datetime.combine(
            bank_transaction.booking_date,
            time.min,
            timezone.utc,
        )

        return calculator.create_opening_balance_adjustment(
            asset_account=counterparty_account,
            opening_balance_account=equity_account,
            adjustment_amount=adjustment_amount,
            adjustment_date=adjustment_datetime,
            iban=counterparty_iban,
            user_id=self._user_id,
            related_transfer_hash=transfer_hash,
        )

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
