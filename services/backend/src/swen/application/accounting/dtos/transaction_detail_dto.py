"""DTOs for transaction detail view."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction


@dataclass(frozen=True)
class JournalEntryDTO:
    """DTO for a single journal entry."""

    account_number: str
    account_name: str
    debit_amount: Optional[Decimal]
    credit_amount: Optional[Decimal]
    currency: str

    @property
    def debit_display(self) -> str:
        if self.debit_amount is not None:
            return f"{self.debit_amount:,.2f}"
        return "-"

    @property
    def credit_display(self) -> str:
        if self.credit_amount is not None:
            return f"{self.credit_amount:,.2f}"
        return "-"


@dataclass(frozen=True)
class TransactionDetailDTO:
    """DTO for detailed transaction view with journal entries."""

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str]
    counterparty_iban: Optional[str]
    source: str
    source_iban: Optional[str]
    is_internal_transfer: bool
    metadata: Optional[dict[str, Any]]
    is_posted: bool
    entries: list[JournalEntryDTO] = field(default_factory=list)
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < Decimal("0.01")

    @property
    def balance_difference(self) -> Decimal:
        return abs(self.total_debit - self.total_credit)

    @property
    def status_display(self) -> str:
        return "Posted" if self.is_posted else "Draft"

    @classmethod
    def from_transaction(cls, txn: Transaction) -> "TransactionDetailDTO":
        entries: list[JournalEntryDTO] = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for entry in txn.entries:
            account = entry.account

            if entry.is_debit():
                debit_amount = entry.debit.amount
                credit_amount = None
                currency = entry.debit.currency.code
                total_debit += debit_amount
            else:
                debit_amount = None
                credit_amount = entry.credit.amount
                currency = entry.credit.currency.code
                total_credit += credit_amount

            entries.append(
                JournalEntryDTO(
                    account_number=account.account_number,
                    account_name=account.name,
                    debit_amount=debit_amount,
                    credit_amount=credit_amount,
                    currency=currency,
                ),
            )

        return cls(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            counterparty=txn.counterparty,
            counterparty_iban=txn.counterparty_iban,
            source=txn.source.value,
            source_iban=txn.source_iban,
            is_internal_transfer=txn.is_internal_transfer,
            metadata=txn.metadata_raw or None,
            is_posted=txn.is_posted,
            entries=entries,
            total_debit=total_debit,
            total_credit=total_credit,
        )
