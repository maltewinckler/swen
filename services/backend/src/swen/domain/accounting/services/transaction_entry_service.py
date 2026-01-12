"""Transaction entry service - core double-entry bookkeeping rules.

This domain service encapsulates the fundamental accounting business rules
for building journal entries. It answers questions like:
- "Which account gets debited in an expense transaction?"
- "How do I swap the category while preserving the payment entry?"

The rules are:
- EXPENSE: Debit Expense, Credit Payment (Asset or Liability)
- INCOME: Debit Payment (Asset or Liability), Credit Income
- ASSET TRANSFER: Debit destination Asset, Credit source Asset
- LIABILITY PAYMENT: Debit Liability (reduces debt), Credit Asset (reduces cash)
- LIABILITY INCREASE: Debit Asset (increases cash), Credit Liability (increases debt)

This service is stateless and has no infrastructure dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.value_objects import Money


class TransactionDirection(Enum):
    """Direction of a simple transaction from the payment account's perspective."""

    EXPENSE = "expense"
    INCOME = "income"


@dataclass(frozen=True)
class EntrySpec:
    """Specification for a journal entry to be created.

    This is a pure data structure describing what entry to create,
    without actually creating it. We use this over JournalEntry to avoid
    the overhead of creating a full JournalEntry object and to keep the service
    stateless.
    """

    account: Account
    amount: Money
    is_debit: bool

    @property
    def is_credit(self) -> bool:
        """True if this is a credit entry."""
        return not self.is_debit

    def __repr__(self) -> str:
        side = "Dr" if self.is_debit else "Cr"
        return f"{side} {self.account.name} {self.amount}"


PAYMENT_ACCOUNT_TYPES = frozenset({AccountType.ASSET, AccountType.LIABILITY})
CATEGORY_ACCOUNT_TYPES = frozenset({AccountType.EXPENSE, AccountType.INCOME})


class TransactionEntryService:
    """Domain service for building journal entries according to accounting rules.

    This service encapsulates the business rules for double-entry bookkeeping.
    It is stateless and operates purely on the provided domain objects (This is why
    we don't use the JournalEntry entity but EntrySpec).
    """

    @staticmethod
    def build_simple_entries(
        payment_account: Account,
        category_account: Account,
        amount: Money,
        direction: TransactionDirection,
    ) -> Tuple[EntrySpec, EntrySpec]:
        TransactionEntryService._validate_payment_account(payment_account)
        TransactionEntryService._validate_category_for_direction(
            category_account,
            direction,
        )

        if direction == TransactionDirection.EXPENSE:
            # Expense: Debit expense, Credit payment
            return (
                EntrySpec(account=category_account, amount=amount, is_debit=True),
                EntrySpec(account=payment_account, amount=amount, is_debit=False),
            )
        # Income: Debit payment, Credit income
        return (
            EntrySpec(account=payment_account, amount=amount, is_debit=True),
            EntrySpec(account=category_account, amount=amount, is_debit=False),
        )

    @staticmethod
    def build_category_swap_entries(
        new_category: Account,
        payment_account: Account,
        amount: Money,
        payment_preserved: bool = False,
    ) -> List[EntrySpec]:
        # Used when recategorizing a transaction - e.g., changing from
        # "Groceries" expense to "Restaurants" expense.
        if new_category.account_type not in CATEGORY_ACCOUNT_TYPES:
            raise InvalidAccountTypeError(
                new_category.account_type.value,
                ["expense", "income"],
            )

        entries: List[EntrySpec] = []

        if new_category.account_type == AccountType.EXPENSE:
            # Expense: Debit expense, Credit payment
            entries.append(
                EntrySpec(account=new_category, amount=amount, is_debit=True),
            )
            if not payment_preserved:
                entries.append(
                    EntrySpec(account=payment_account, amount=amount, is_debit=False),
                )
        else:
            # Income: Debit payment, Credit income
            if not payment_preserved:
                entries.append(
                    EntrySpec(account=payment_account, amount=amount, is_debit=True),
                )
            entries.append(
                EntrySpec(account=new_category, amount=amount, is_debit=False),
            )

        return entries

    @staticmethod
    def build_internal_transfer_entries(
        source_account: Account,
        destination_account: Account,
        amount: Money,
        source_preserved: bool = False,
    ) -> List[EntrySpec]:
        entries: List[EntrySpec] = []

        # Debit destination (increases), Credit source (decreases)
        entries.append(
            EntrySpec(account=destination_account, amount=amount, is_debit=True),
        )
        if not source_preserved:
            entries.append(
                EntrySpec(account=source_account, amount=amount, is_debit=False),
            )

        return entries

    @staticmethod
    def build_liability_payment_entries(
        asset_account: Account,
        liability_account: Account,
        amount: Money,
        is_payment_out: bool,
        asset_preserved: bool = False,
    ) -> List[EntrySpec]:
        entries: List[EntrySpec] = []

        if is_payment_out:
            # Payment to liability: Debit Liability (reduces debt), Credit Asset
            entries.append(
                EntrySpec(account=liability_account, amount=amount, is_debit=True),
            )
            if not asset_preserved:
                entries.append(
                    EntrySpec(account=asset_account, amount=amount, is_debit=False),
                )
        else:
            # Payout from liability: Debit Asset (increases cash), Credit Liability
            if not asset_preserved:
                entries.append(
                    EntrySpec(account=asset_account, amount=amount, is_debit=True),
                )
            entries.append(
                EntrySpec(account=liability_account, amount=amount, is_debit=False),
            )

        return entries

    @staticmethod
    def determine_direction_from_amount(amount_signed: Money) -> TransactionDirection:
        if amount_signed.amount < 0:
            return TransactionDirection.EXPENSE
        return TransactionDirection.INCOME

    @staticmethod
    def find_payment_entry(
        entries: List["EntrySpec"],
    ) -> Optional["EntrySpec"]:
        for entry in entries:
            if entry.account.account_type in PAYMENT_ACCOUNT_TYPES:
                return entry
        return None

    @staticmethod
    def find_category_entry(
        entries: List["EntrySpec"],
    ) -> Optional["EntrySpec"]:
        for entry in entries:
            if entry.account.account_type in CATEGORY_ACCOUNT_TYPES:
                return entry
        return None

    @staticmethod
    def _validate_payment_account(account: Account) -> None:
        if account.account_type not in PAYMENT_ACCOUNT_TYPES:
            raise InvalidAccountTypeError(
                account.account_type.value,
                ["asset", "liability"],
            )

    @staticmethod
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
