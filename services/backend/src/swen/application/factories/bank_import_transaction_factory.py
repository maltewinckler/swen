"""Factory for creating accounting transactions from bank imports.

This factory encapsulates the logic for transforming bank transactions into
double-entry accounting transactions, including:
- Journal entry creation (debits/credits)
- Metadata attachment (source, counterparty, AI resolution)
- Description generation

Extracted from TransactionImportService for single responsibility.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, Optional

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.value_objects import (
    AIResolutionMetadata,
    Money,
    TransactionMetadata,
    TransactionSource,
)
from swen.domain.banking.value_objects import BankTransaction

if TYPE_CHECKING:
    from swen.domain.shared.current_user import CurrentUser

logger = logging.getLogger(__name__)


class BankImportTransactionFactory:
    """Factory for creating accounting transactions from bank imports."""

    def __init__(
        self,
        current_user: CurrentUser,
    ):
        self._current_user = current_user

    @property
    def _user_id(self):
        return self._current_user.user_id

    def create(  # NOQA: PLR0913
        self,
        bank_transaction: BankTransaction,
        asset_account: Account,
        counter_account: Account,
        source_iban: str,
        is_internal_transfer: bool = False,
        ai_resolution: Optional[AIResolutionMetadata] = None,
    ) -> Transaction:
        """
        Create a double-entry accounting transaction from a bank transaction.

        Rules for external transactions:
        - Money OUT (negative amount): Debit Expense, Credit Asset
        - Money IN (positive amount): Debit Asset, Credit Income

        Rules for internal transfers:
        - Money OUT (negative amount): Debit DestAsset, Credit SourceAsset
        - Money IN (positive amount): Debit SourceAsset, Credit DestAsset
        """
        description = self._generate_description(
            bank_transaction,
            is_internal_transfer=is_internal_transfer,
            counterparty_account=counter_account if is_internal_transfer else None,
        )

        booking_timestamp = datetime.combine(
            bank_transaction.booking_date,
            time.min,
            timezone.utc,
        )

        counterparty_name = (
            counter_account.name
            if is_internal_transfer
            else bank_transaction.applicant_name
        )

        transaction = Transaction(
            description=description,
            user_id=self._user_id,
            date=booking_timestamp,
            counterparty=counterparty_name,
            counterparty_iban=bank_transaction.applicant_iban,
            source=TransactionSource.BANK_IMPORT,
            source_iban=source_iban,
            is_internal_transfer=is_internal_transfer,
        )

        self._add_journal_entries(
            transaction=transaction,
            bank_transaction=bank_transaction,
            asset_account=asset_account,
            counter_account=counter_account,
            is_internal_transfer=is_internal_transfer,
        )

        metadata = self._build_metadata(
            bank_transaction=bank_transaction,
            asset_account=asset_account,
            counter_account=counter_account,
            is_internal_transfer=is_internal_transfer,
            source_iban=source_iban,
            ai_resolution=ai_resolution,
        )
        transaction.set_metadata(metadata)

        return transaction

    def _add_journal_entries(
        self,
        transaction: Transaction,
        bank_transaction: BankTransaction,
        asset_account: Account,
        counter_account: Account,
        is_internal_transfer: bool,
    ):
        money = Money(
            amount=abs(bank_transaction.amount),
            currency=bank_transaction.currency,
        )

        if is_internal_transfer:
            if bank_transaction.is_debit():  # Money OUT from source
                transaction.add_debit(counter_account, money)  # Destination asset
                transaction.add_credit(asset_account, money)  # Source asset
            else:  # Money IN to source
                transaction.add_debit(asset_account, money)  # Source asset
                transaction.add_credit(counter_account, money)  # Destination asset
        elif bank_transaction.is_debit():  # External: Money OUT
            transaction.add_debit(counter_account, money)  # Expense account
            transaction.add_credit(asset_account, money)  # Bank account
        else:  # External: Money IN
            transaction.add_debit(asset_account, money)  # Bank account
            transaction.add_credit(counter_account, money)  # Income account

    def _build_metadata(  # NOQA: PLR0913
        self,
        bank_transaction: BankTransaction,
        asset_account: Account,
        counter_account: Account,
        is_internal_transfer: bool,
        source_iban: str,
        ai_resolution: Optional[AIResolutionMetadata] = None,
    ) -> TransactionMetadata:
        transfer_hash: Optional[str] = None
        if bank_transaction.applicant_iban:
            transfer_hash = bank_transaction.compute_transfer_identity_hash(
                source_iban,
                bank_transaction.applicant_iban,
            )

        return TransactionMetadata(
            source=TransactionSource.BANK_IMPORT,
            original_purpose=bank_transaction.purpose,
            bank_reference=bank_transaction.bank_reference,
            source_account=asset_account.name if is_internal_transfer else None,
            destination_account=counter_account.name if is_internal_transfer else None,
            transfer_identity_hash=transfer_hash,
            ai_resolution=ai_resolution,
        )

    def _generate_description(
        self,
        bank_transaction: BankTransaction,
        is_internal_transfer: bool = False,
        counterparty_account: Account | None = None,
    ) -> str:
        if is_internal_transfer and counterparty_account:
            direction = "from" if bank_transaction.is_credit() else "to"
            return f"Transfer {direction} {counterparty_account.name}"

        purpose = bank_transaction.purpose.strip() if bank_transaction.purpose else ""
        if purpose:
            return purpose[:100]

        if bank_transaction.applicant_name:
            return f"Transaction with {bank_transaction.applicant_name}"

        return "Bank transaction"
