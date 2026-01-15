"""Service for detecting and reconciling internal transfers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Optional

from swen.application.queries.integration import OpeningBalanceQuery
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType, JournalEntry
from swen.domain.accounting.services import (
    CATEGORY_ACCOUNT_TYPES,
    TransactionEntryService,
)
from swen.domain.accounting.value_objects import MetadataKeys
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.repositories import AccountMappingRepository

logger = logging.getLogger(__name__)


@dataclass
class TransferContext:
    """Context for internal transfer detection."""

    counterparty_iban: str | None
    counterparty_account: Account | None
    counterparty_opening_balance_date: date | None = None

    @property
    def is_internal_transfer(self) -> bool:
        return self.counterparty_account is not None

    @property
    def is_asset_transfer(self) -> bool:
        return (
            self.counterparty_account is not None
            and self.counterparty_account.account_type == AccountType.ASSET
        )

    @property
    def is_liability_transfer(self) -> bool:
        return (
            self.counterparty_account is not None
            and self.counterparty_account.account_type == AccountType.LIABILITY
        )

    @property
    def can_reconcile(self) -> bool:
        return self.is_asset_transfer and self.counterparty_iban is not None

    def is_pre_opening_balance(self, transaction_date: date) -> bool:
        """
        Check if a transaction date predates the counterparty's opening balance.

        This is used to determine if an internal transfer requires an opening
        balance adjustment on the counterparty account.
        """
        if self.counterparty_opening_balance_date is None:
            return False
        return transaction_date < self.counterparty_opening_balance_date

    @classmethod
    def not_a_transfer(cls) -> TransferContext:
        return cls(counterparty_iban=None, counterparty_account=None)

    @classmethod
    def external_counterparty(cls, iban: str) -> TransferContext:
        return cls(counterparty_iban=iban, counterparty_account=None)


class TransferReconciliationService:
    """Service for detecting and reconciling internal transfers."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        mapping_repository: AccountMappingRepository,
        account_repository: AccountRepository,
        opening_balance_query: OpeningBalanceQuery | None = None,
    ):
        self._transaction_repo: TransactionRepository = transaction_repository
        self._mapping_repo: AccountMappingRepository = mapping_repository
        self._account_repo: AccountRepository = account_repository
        self._ob_query = opening_balance_query

    async def detect_transfer(
        self,
        bank_transaction: BankTransaction,
    ) -> TransferContext:
        counterparty_iban = normalize_iban(bank_transaction.applicant_iban)
        if not counterparty_iban:
            return TransferContext.not_a_transfer()

        counterparty_mapping = await self._mapping_repo.find_by_iban(counterparty_iban)
        if not counterparty_mapping:
            return TransferContext.external_counterparty(counterparty_iban)

        counterparty_account = await self._account_repo.find_by_id(
            counterparty_mapping.accounting_account_id,
        )

        # Fetch the counterparty's opening balance date for pre-OB transfer detection
        counterparty_ob_date = None
        if self._ob_query is not None:
            counterparty_ob_date = await self._ob_query.get_date_for_iban(
                counterparty_iban,
            )

        return TransferContext(
            counterparty_iban=counterparty_iban,
            counterparty_account=counterparty_account,
            counterparty_opening_balance_date=counterparty_ob_date,
        )

    async def find_matching_transfer(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        counterparty_iban: str,
        date_tolerance_days: int = 2,
    ) -> Optional[Transaction]:
        transfer_hash = bank_transaction.compute_transfer_identity_hash(
            source_iban,
            counterparty_iban,
        )
        exact_match = await self._find_by_transfer_hash(transfer_hash)
        if exact_match:
            return exact_match

        return await self._find_fuzzy_match(
            bank_transaction=bank_transaction,
            source_iban=source_iban,
            date_tolerance_days=date_tolerance_days,
        )

    async def _find_by_transfer_hash(
        self,
        transfer_hash: str,
    ) -> Optional[Transaction]:
        transactions = await self._transaction_repo.find_by_metadata(
            MetadataKeys.TRANSFER_IDENTITY_HASH,
            transfer_hash,
        )
        return transactions[0] if transactions else None

    async def _find_fuzzy_match(
        self,
        bank_transaction: BankTransaction,
        source_iban: str,
        date_tolerance_days: int,
    ) -> Optional[Transaction]:
        candidates = await self._transaction_repo.find_by_counterparty_iban(source_iban)

        amount = abs(bank_transaction.amount)
        booking_date = bank_transaction.booking_date

        for candidate in candidates:
            if candidate.total_amount().amount != amount:
                continue

            candidate_date = candidate.date.date()
            date_diff = abs((booking_date - candidate_date).days)
            if date_diff > date_tolerance_days:
                continue

            logger.debug(
                "Found potential transfer match: %s (date diff: %d days)",
                candidate.id,
                date_diff,
            )
            return candidate

        return None

    async def convert_to_internal_transfer(
        self,
        transaction: Transaction,
        new_asset_account: Account,
        counterparty_iban: str,
        source_iban: str,
    ) -> bool:
        transfer_hash = BankTransaction.compute_transfer_hash(
            iban_a=source_iban,
            iban_b=counterparty_iban,
            booking_date=transaction.date.date(),
            amount=transaction.total_amount().amount,
        )

        converted = transaction.convert_to_internal_transfer(
            new_asset_account=new_asset_account,
            transfer_hash=transfer_hash,
        )

        if not converted:
            logger.warning(
                "Cannot convert transaction %s: no Income/Expense entry found",
                transaction.id,
            )
            return False

        await self._transaction_repo.save(transaction)

        logger.info(
            "Converted transaction %s to internal transfer to %s",
            transaction.id,
            new_asset_account.name,
        )
        return True

    async def reconcile_for_new_account(
        self,
        iban: str,
        asset_account: Account,
    ) -> int:
        candidates = await self._transaction_repo.find_by_counterparty_iban(iban)

        reconciled = 0
        for transaction in candidates:
            if transaction.is_internal_transfer:
                continue

            source_iban = self._get_source_iban_from_transaction(transaction)
            try:
                success = await self.convert_to_internal_transfer(
                    transaction=transaction,
                    new_asset_account=asset_account,
                    counterparty_iban=iban,
                    source_iban=source_iban,
                )
                if success:
                    reconciled += 1
            except Exception as e:
                logger.warning(
                    "Failed to reconcile transaction %s: %s",
                    transaction.id,
                    e,
                )

        if reconciled > 0:
            logger.info(
                "Reconciled %d transaction(s) as internal transfers to %s",
                reconciled,
                asset_account.name,
            )

        return reconciled

    def _get_source_iban_from_transaction(self, transaction: Transaction) -> str:
        return transaction.source_iban or ""

    async def reconcile_liability_for_new_account(
        self,
        iban: str,
        liability_account: Account,
    ) -> int:
        candidates = await self._transaction_repo.find_by_counterparty_iban(iban)

        reconciled = 0
        for transaction in candidates:
            if transaction.is_internal_transfer:
                continue
            try:
                success = await self._convert_to_liability_payment(
                    transaction=transaction,
                    liability_account=liability_account,
                )
                if success:
                    reconciled += 1
            except Exception as e:
                logger.warning(
                    "Failed to reconcile liability transaction %s: %s",
                    transaction.id,
                    e,
                )

        if reconciled > 0:
            logger.info(
                "Reconciled %d transaction(s) as liability payments to %s",
                reconciled,
                liability_account.name,
            )

        return reconciled

    def _find_conversion_entries(
        self,
        transaction: Transaction,
    ) -> tuple[JournalEntry, JournalEntry] | None:
        expense_income_entry = None
        asset_entry = None
        for entry in transaction.entries:
            if entry.account.account_type in CATEGORY_ACCOUNT_TYPES:
                expense_income_entry = entry
            elif entry.account.account_type == AccountType.ASSET:
                asset_entry = entry

        if not expense_income_entry:
            logger.warning(
                "Cannot convert transaction %s: no Expense/Income entry found",
                transaction.id,
            )
            return None

        if not asset_entry:
            logger.warning(
                "Cannot convert transaction %s: no Asset entry found",
                transaction.id,
            )
            return None

        return expense_income_entry, asset_entry

    def _rebuild_as_liability_payment(
        self,
        transaction: Transaction,
        liability_account: Account,
        expense_income_entry: JournalEntry,
        asset_entry: JournalEntry,
    ):
        amount = expense_income_entry.amount
        transaction.clear_entries()

        asset_preserved = any(
            e.account.account_type == AccountType.ASSET for e in transaction.entries
        )
        is_payment_out = expense_income_entry.is_debit()

        entry_specs = TransactionEntryService.build_liability_payment_entries(
            asset_account=asset_entry.account,
            liability_account=liability_account,
            amount=amount,
            is_payment_out=is_payment_out,
            asset_preserved=asset_preserved,
        )

        for spec in entry_specs:
            if spec.is_debit:
                transaction.add_debit(spec.account, spec.amount)
            else:
                transaction.add_credit(spec.account, spec.amount)

        description = (
            f"Payment to {liability_account.name}"
            if is_payment_out
            else f"Transfer from {liability_account.name}"
        )
        transaction.update_description(description)
        transaction.update_counterparty(liability_account.name)
        transaction._is_internal_transfer = True
        transaction.update_metadata(
            source_account=asset_entry.account.name,
            destination_account=liability_account.name,
        )

    async def _convert_to_liability_payment(
        self,
        transaction: Transaction,
        liability_account: Account,
    ) -> bool:
        entries = self._find_conversion_entries(transaction)
        if entries is None:
            return False
        expense_income_entry, asset_entry = entries

        was_posted = transaction.is_posted
        if was_posted:
            transaction.unpost()

        try:
            self._rebuild_as_liability_payment(
                transaction,
                liability_account,
                expense_income_entry,
                asset_entry,
            )
        finally:
            if was_posted:
                transaction.post()

        await self._transaction_repo.save(transaction)

        logger.info(
            "Converted transaction %s to liability payment to %s",
            transaction.id,
            liability_account.name,
        )
        return True
