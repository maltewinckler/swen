"""Transaction entry service - core double-entry bookkeeping rules.

This domain service encapsulates the fundamental accounting business rules
for building journal entries. It answers questions like:
- "Which account gets debited in an expense transaction?"
- "How do I swap the category while preserving the payment entry?"

The rules are:
- EXPENSE: Debit Expense, Credit Payment (Asset or Liability)
- INCOME: Debit Payment (Asset or Liability), Credit Income
- ASSET TRANSFER: Debit destination Asset, Credit source Asset

This service is stateless and has no infrastructure dependencies.
"""

from enum import Enum
from typing import Tuple

from swen.domain.accounting.entities import (
    Account,
    AccountType,
)
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.value_objects import (
    JournalEntryInput,
    Money,
)


class TransactionDirection(Enum):
    """Direction of a simple transaction from the payment account's perspective."""

    EXPENSE = "expense"
    INCOME = "income"


def _validate_payment_account(account: Account) -> None:
    if account.account_type not in (AccountType.ASSET, AccountType.LIABILITY):
        raise InvalidAccountTypeError(
            account.account_type.value,
            ["asset", "liability"],
        )


def _validate_category_for_direction(
    account: Account,
    direction: TransactionDirection,
) -> None:
    expected_type = (
        AccountType.EXPENSE
        if direction == TransactionDirection.EXPENSE
        else AccountType.INCOME
    )
    if account.account_type != expected_type:
        raise InvalidAccountTypeError(
            account.account_type.value,
            [expected_type.value],
        )


class TransactionEntryService:
    """Domain service for building journal entries according to accounting rules.

    This service encapsulates the business rules for double-entry bookkeeping.
    It is stateless and operates purely on the provided domain objects.
    """

    @staticmethod
    def resolve_transaction_direction(is_expense: bool) -> TransactionDirection:
        """Determine the transaction direction based on whether it's an expense."""
        return (
            TransactionDirection.EXPENSE if is_expense else TransactionDirection.INCOME
        )

    @staticmethod
    def build_simple_entries(
        payment_account: Account,
        category_account: Account,
        amount: Money,
        is_expense: bool,
    ) -> Tuple[JournalEntryInput, JournalEntryInput]:
        direction = TransactionEntryService.resolve_transaction_direction(is_expense)

        _validate_payment_account(payment_account)
        _validate_category_for_direction(category_account, direction)

        if direction == TransactionDirection.EXPENSE:
            # Expense: Debit expense, Credit payment
            return (
                JournalEntryInput.debit_entry(category_account.id, amount.amount),
                JournalEntryInput.credit_entry(payment_account.id, amount.amount),
            )
        # Income: Debit payment, Credit income
        return (
            JournalEntryInput.debit_entry(payment_account.id, amount.amount),
            JournalEntryInput.credit_entry(category_account.id, amount.amount),
        )
