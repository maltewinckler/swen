"""Domain service for analyzing transaction journal entry structure."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from swen.domain.accounting.entities import PAYMENT_ACCOUNT_TYPES, JournalEntry
from swen.domain.accounting.value_objects import Currency, Money

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction


class TransactionAnalyzer:
    """Analyzes the accounting meaning of a transaction's journal entries.

    This service provides a single, canonical source for interpreting the
    double-entry structure of a :class:`Transaction`.  All DTOs and other
    consumers should delegate to this class rather than reimplementing the
    entry-iteration logic.

    Each method returns a single, well-named value so callers can pick
    exactly what they need without unpacking tuples or dataclasses.
    """

    @staticmethod
    def debit_account_name(txn: Transaction) -> Optional[str]:
        """Return the name of the debit account.

        Returns ``"Split"`` when a transaction has multiple debit entries.
        """
        if not txn.entries:
            return None

        debit_entries: List[JournalEntry] = [e for e in txn.entries if e.is_debit()]
        if len(debit_entries) == 1:
            return debit_entries[0].account.name
        if len(debit_entries) > 1:
            return "Split"
        return None

    @staticmethod
    def credit_account_name(txn: Transaction) -> Optional[str]:
        """Return the name of the credit account.

        Returns ``"Split"`` when a transaction has multiple credit entries.
        """
        if not txn.entries:
            return None

        credit_entries: List[JournalEntry] = [
            e for e in txn.entries if not e.is_debit()
        ]
        if len(credit_entries) == 1:
            return credit_entries[0].account.name
        if len(credit_entries) > 1:
            return "Split"
        return None

    @staticmethod
    def counter_account_name(txn: Transaction) -> Optional[str]:
        """Return the non-payment account name for a transaction.

        The counter-account is the account that is *not* the payment account
        (i.e. the category, income, expense, or other asset/liability account
        on the other side of the journal entry).  Returns ``"Split"`` when
        there are multiple counter-entries.

        For internal transfers between two payment accounts (e.g. Asset
        to Asset), the counter-account is the other payment account.
        """
        if not txn.entries:
            return None

        payment_entry = TransactionAnalyzer.payment_side(txn)
        if payment_entry is None:
            return None

        # Find entries that are not the payment entry
        non_payment_entries: List[JournalEntry] = [
            e for e in txn.entries if e != payment_entry
        ]

        if not non_payment_entries:
            return None

        # For split detection, only count non-payment-type accounts
        # (this matches the original behavior where internal transfers
        # between two asset accounts don't show "Split")
        counter_entries = [
            e
            for e in non_payment_entries
            if e.account.account_type not in PAYMENT_ACCOUNT_TYPES
        ]

        if len(counter_entries) > 1:
            return "Split"

        # If there are non-payment counter entries, use the first one
        if counter_entries:
            return counter_entries[0].account.name

        # Fallback: for internal transfers between payment accounts,
        # return the first non-payment entry's account name
        return non_payment_entries[0].account.name

    @staticmethod
    def payment_side(txn: Transaction) -> Optional[JournalEntry]:
        """Return the main payment-account entry for a transaction.

        Priority:
        1. Entry matching :attr:`Transaction.source_iban` (if set)
        2. First entry whose account is a payment type (ASSET / LIABILITY)
        3. First entry overall (fallback for legacy / manual transactions)
        """
        source_iban = txn.source_iban
        if source_iban:
            for entry in txn.entries:
                if entry.account.iban and entry.account.iban == source_iban:
                    return entry

        for entry in txn.entries:
            if entry.account.account_type in PAYMENT_ACCOUNT_TYPES:
                return entry

        return txn.entries[0] if txn.entries else None

    @staticmethod
    def payment_amount(txn: Transaction) -> Decimal:
        """Return the amount on the payment side of the transaction."""
        payment_entry = TransactionAnalyzer.payment_side(txn)
        if payment_entry is None:
            return Decimal(0)
        return (
            payment_entry.debit.amount
            if payment_entry.is_debit()
            else payment_entry.credit.amount
        )

    @staticmethod
    def payment_currency(txn: Transaction) -> str:
        """Return the currency of the payment side of the transaction."""
        payment_entry = TransactionAnalyzer.payment_side(txn)
        if payment_entry is None:
            return Currency.default().code
        return (
            payment_entry.debit.currency.code
            if payment_entry.is_debit()
            else payment_entry.credit.currency.code
        )

    @staticmethod
    def is_income(txn: Transaction) -> bool:
        """Return whether the transaction represents income.

        A debit on the payment account means money came in (income).
        A credit on the payment account means money went out (expense).
        """
        payment_entry = TransactionAnalyzer.payment_side(txn)
        if payment_entry is None:
            return True  # default
        return payment_entry.is_debit()

    @staticmethod
    def total_amount(txn: Transaction) -> Money:
        """Return the total absolute amount of the transaction.

        For a balanced double-entry transaction this is the sum of all
        debits (which equals the sum of all credits).
        """
        if not txn.entries:
            return Money(Decimal(0), Currency.default())

        first = txn.entries[0]
        currency = (first.debit if first.is_debit() else first.credit).currency
        total = Money(Decimal(0), currency)

        for entry in txn.entries:
            if entry.is_debit():
                total = total + entry.debit

        return total

    @staticmethod
    def debit_credit_totals(txn: Transaction) -> tuple[Decimal, Decimal]:
        """Return (total_debit, total_credit) for a transaction.

        Used by DTOs that need both totals for display or balance checking.
        """
        total_debit = Decimal(0)
        total_credit = Decimal(0)

        for entry in txn.entries:
            if entry.is_debit():
                total_debit = total_debit + entry.debit.amount
            else:
                total_credit = total_credit + entry.credit.amount

        return total_debit, total_credit
