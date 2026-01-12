"""DTOs for transaction listing."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import JournalEntry
from swen.domain.accounting.entities.account_type import AccountType

# Account types that represent payment accounts (bank accounts, credit cards)
PAYMENT_ACCOUNT_TYPES = frozenset({AccountType.ASSET, AccountType.LIABILITY})


@dataclass(frozen=True)
class TransactionListItemDTO:
    """DTO for a transaction in a list view."""

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str]
    counter_account: Optional[str]
    debit_account: Optional[str]
    credit_account: Optional[str]
    amount: Decimal
    currency: str
    is_income: bool
    is_posted: bool
    is_internal_transfer: bool
    short_id: str

    @property
    def amount_display(self) -> str:
        sign = "+" if self.is_income else "-"
        return f"{sign}{self.amount:,.2f}"

    @property
    def status_display(self) -> str:
        return "Posted" if self.is_posted else "Draft"

    @classmethod
    def from_transaction(cls, txn: Transaction) -> "TransactionListItemDTO":
        debit_account_name, credit_account_name = _extract_debit_credit_names(txn)
        counter_account_name = _extract_counter_account_name(txn)
        amount, currency, is_income = _extract_amount_info(txn)

        return cls(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            counterparty=txn.counterparty,
            counter_account=counter_account_name,
            debit_account=debit_account_name,
            credit_account=credit_account_name,
            amount=amount,
            currency=currency,
            is_income=is_income,
            is_posted=txn.is_posted,
            is_internal_transfer=txn.is_internal_transfer,
            short_id=str(txn.id)[:8],
        )


def _extract_debit_credit_names(
    txn: Transaction,
) -> tuple[Optional[str], Optional[str]]:
    """Extract debit and credit account names from transaction entries."""
    if not txn.entries:
        return None, None

    debit_entries = [e for e in txn.entries if e.is_debit()]
    credit_entries = [e for e in txn.entries if not e.is_debit()]

    debit_name: Optional[str] = None
    if len(debit_entries) == 1:
        debit_name = debit_entries[0].account.name
    elif len(debit_entries) > 1:
        debit_name = "Split"

    credit_name: Optional[str] = None
    if len(credit_entries) == 1:
        credit_name = credit_entries[0].account.name
    elif len(credit_entries) > 1:
        credit_name = "Split"

    return debit_name, credit_name


def _extract_counter_account_name(txn: Transaction) -> Optional[str]:
    """Extract the counter-account name from a transaction."""
    if not txn.entries:
        return None

    payment_entry = _find_payment_entry(txn)
    counter_entry = _find_counter_entry(txn, payment_entry)

    if not counter_entry:
        return None

    # Check if there are multiple counter entries (split)
    counter_entries = [
        e
        for e in txn.entries
        if e != payment_entry and e.account.account_type not in PAYMENT_ACCOUNT_TYPES
    ]

    if len(counter_entries) > 1:
        return "Split"

    return counter_entry.account.name


def _extract_amount_info(txn: Transaction) -> tuple[Decimal, str, bool]:
    """Extract amount, currency, and income/expense direction from transaction."""
    if not txn.entries:
        return Decimal("0"), "EUR", True

    payment_entry = _find_payment_entry(txn)
    if payment_entry:
        return _determine_amount_and_direction(payment_entry)

    return Decimal("0"), "EUR", True


def _find_payment_entry(txn: Transaction) -> Optional[JournalEntry]:
    """Find the main payment account entry in a transaction."""
    source_iban = txn.source_iban
    if source_iban:
        for entry in txn.entries:
            if entry.account.iban and entry.account.iban == source_iban:
                return entry

    for entry in txn.entries:
        if entry.account.account_type in PAYMENT_ACCOUNT_TYPES:
            return entry

    return txn.entries[0] if txn.entries else None


def _find_counter_entry(
    txn: Transaction,
    payment_entry: Optional[JournalEntry],
) -> Optional[JournalEntry]:
    """Find the counter-account entry in a transaction."""
    if not payment_entry:
        return None

    for entry in txn.entries:
        if entry != payment_entry:
            return entry

    return None


def _determine_amount_and_direction(
    payment_entry: JournalEntry,
) -> tuple[Decimal, str, bool]:
    """Determine amount, currency, and income/expense direction from payment entry."""
    if payment_entry.is_debit():
        amount = payment_entry.debit.amount
        currency = payment_entry.debit.currency.code
        is_income = True
    else:
        amount = payment_entry.credit.amount
        currency = payment_entry.credit.currency.code
        is_income = False

    return amount, currency, is_income


@dataclass(frozen=True)
class TransactionListResultDTO:
    """Result of listing transactions."""

    transactions: list[TransactionListItemDTO] = field(default_factory=list)
    total_count: int = 0

    @property
    def is_empty(self) -> bool:
        return len(self.transactions) == 0
