"""DTOs for transaction listing."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.services import TransactionAnalyzer


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
        return cls(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            counterparty=txn.counterparty,
            counter_account=TransactionAnalyzer.counter_account_name(txn),
            debit_account=TransactionAnalyzer.debit_account_name(txn),
            credit_account=TransactionAnalyzer.credit_account_name(txn),
            amount=TransactionAnalyzer.payment_amount(txn),
            currency=TransactionAnalyzer.payment_currency(txn),
            is_income=TransactionAnalyzer.is_income(txn),
            is_posted=txn.is_posted,
            is_internal_transfer=txn.is_internal_transfer,
            short_id=str(txn.id)[:8],
        )


@dataclass(frozen=True)
class TransactionListResultDTO:
    """Result of listing transactions."""

    transactions: list[TransactionListItemDTO] = field(default_factory=list)
    total_count: int = 0

    @property
    def is_empty(self) -> bool:
        return len(self.transactions) == 0
