"""Domain service for creating opening balance entries.

Opening balance entries are used to set the initial state of an account
when first connecting it to the accounting system. This is required because
we sync historical transactions but need to establish a starting point.

The opening balance is back-calculated from:
- Current balance (from bank)
- Sum of historical transactions being imported

Formula: opening_balance = current_balance - net_change_from_transactions
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.value_objects import (
    MetadataKeys,
    Money,
    TransactionMetadata,
    TransactionSource,
)

if TYPE_CHECKING:
    from swen.domain.banking.value_objects import BankTransaction


# Deprecated: Use MetadataKeys.IS_OPENING_BALANCE and MetadataKeys.OPENING_BALANCE_IBAN
# Kept for backward compatibility during migration
OPENING_BALANCE_METADATA_KEY = MetadataKeys.IS_OPENING_BALANCE
OPENING_BALANCE_IBAN_KEY = MetadataKeys.OPENING_BALANCE_IBAN


class OpeningBalanceService:
    """
    Domain service for creating opening balance entries.

    This service handles the creation of opening balance transactions
    which establish the initial state of a bank account in the accounting system.

    The opening balance is typically created during the first sync when:
    1. We know the current balance (from bank)
    2. We have historical transactions to import
    3. We can back-calculate what the balance was before those transactions

    Layer: Domain (pure business logic, no infrastructure dependencies)
    """

    def calculate_opening_balance(
        self,
        current_balance: Decimal,
        bank_transactions: "list[BankTransaction]",
    ) -> Decimal:
        """
        Back-calculate opening balance from current balance and transactions.

        Formula: opening_balance = current_balance - net_change

        Where net_change is the sum of all transaction amounts:
        - Positive amounts (credits) increase the balance
        - Negative amounts (debits) decrease the balance

        Parameters
        ----------
        current_balance
            Current balance as reported by the bank
        bank_transactions
            List of transactions being imported
        """
        net_change = sum(txn.amount for txn in bank_transactions)
        return current_balance - net_change

    def create_opening_balance_transaction(
        self,
        asset_account: Account,
        opening_balance_account: Account,
        amount: Decimal,
        currency: str,
        balance_date: datetime,
        iban: str,
        user_id: UUID,
    ) -> Transaction | None:
        """
        Create a balanced opening balance transaction.

        This creates a double-entry transaction:
        - For positive balance: Debit Asset, Credit Equity
        - For negative balance (overdraft): Credit Asset, Debit Equity

        The transaction is automatically posted since it's a system-generated
        entry that establishes the initial state.
        """
        # Validate account types
        if asset_account.account_type != AccountType.ASSET:
            raise InvalidAccountTypeError(
                str(asset_account.account_type),
                ["ASSET"],
            )

        if opening_balance_account.account_type != AccountType.EQUITY:
            raise InvalidAccountTypeError(
                str(opening_balance_account.account_type),
                ["EQUITY"],
            )

        # If opening balance is zero, we don't create a transaction.
        # Creating two zero-amount journal entries is not useful and can cause
        # ambiguity in downstream logic (and is disallowed by the Transaction aggregate).
        if amount == 0:
            return None

        # Build typed metadata
        metadata = TransactionMetadata(
            source=TransactionSource.OPENING_BALANCE,
            is_opening_balance=True,
            opening_balance_iban=iban,
        )

        # Create transaction
        txn = Transaction(
            description=f"Opening Balance - {asset_account.name}",
            user_id=user_id,
            date=balance_date,
        )
        txn.set_metadata(metadata)

        # Create money value object with absolute amount
        money = Money(amount=str(abs(amount)), currency=currency)

        if amount >= 0:
            # Positive balance: Debit Asset (increases), Credit Equity (increases)
            txn.add_debit(asset_account, money)
            txn.add_credit(opening_balance_account, money)
        else:
            # Negative balance (overdraft): Credit Asset (decreases), Debit Equity
            txn.add_credit(asset_account, money)
            txn.add_debit(opening_balance_account, money)

        # Auto-post system-generated entry
        txn.post()

        return txn

    def get_earliest_transaction_date(
        self,
        bank_transactions: "list[BankTransaction]",
    ) -> datetime | None:
        """
        Get the earliest booking date from a list of transactions.

        This is used to determine the date for the opening balance entry,
        which should be at or before the earliest transaction.
        """
        if not bank_transactions:
            return None

        earliest_date = min(txn.booking_date for txn in bank_transactions)

        # Convert date to datetime at start of day (UTC)
        return datetime.combine(
            earliest_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
