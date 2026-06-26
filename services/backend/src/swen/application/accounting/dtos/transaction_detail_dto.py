"""DTOs for transaction detail view."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.services import TransactionAnalyzer


class JournalEntryDTO(BaseModel):
    """DTO for a single journal entry."""

    model_config = ConfigDict(frozen=True)

    account_number: str
    account_name: str
    debit_amount: Optional[Decimal] = None
    credit_amount: Optional[Decimal] = None
    currency: str

    @computed_field
    @property
    def debit_display(self) -> str:
        if self.debit_amount is not None:
            return f"{self.debit_amount:,.2f}"
        return "-"

    @computed_field
    @property
    def credit_display(self) -> str:
        if self.credit_amount is not None:
            return f"{self.credit_amount:,.2f}"
        return "-"


class TransactionDetailDTO(BaseModel):
    """DTO for detailed transaction view with journal entries."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str] = None
    counterparty_iban: Optional[str] = None
    source: str
    source_iban: Optional[str] = None
    is_internal_transfer: bool
    metadata: Optional[dict[str, Any]] = None
    is_posted: bool
    entries: list[JournalEntryDTO] = []
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")

    @computed_field
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < Decimal("0.01")

    @computed_field
    @property
    def balance_difference(self) -> Decimal:
        return abs(self.total_debit - self.total_credit)

    @computed_field
    @property
    def status_display(self) -> str:
        return "Posted" if self.is_posted else "Draft"

    @classmethod
    def from_transaction(cls, txn: Transaction) -> TransactionDetailDTO:
        entries: list[JournalEntryDTO] = []

        for entry in txn.entries:
            account = entry.account

            if entry.is_debit():
                debit_amount = entry.debit.amount
                credit_amount: Optional[Decimal] = None
                currency = entry.debit.currency.code
            else:
                debit_amount = None
                credit_amount = entry.credit.amount
                currency = entry.credit.currency.code

            entries.append(
                JournalEntryDTO(
                    account_number=account.account_number,
                    account_name=account.name,
                    debit_amount=debit_amount,
                    credit_amount=credit_amount,
                    currency=currency,
                ),
            )

        total_debit, total_credit = TransactionAnalyzer.debit_credit_totals(txn)

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
