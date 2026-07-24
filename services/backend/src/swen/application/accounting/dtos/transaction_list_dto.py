"""DTOs for transaction listing."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.services import TransactionAnalyzer


class TransactionListItemDTO(BaseModel):
    """DTO for a transaction in a list view."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str] = None
    counter_account: Optional[str] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    amount: Decimal
    currency: str
    is_income: bool
    is_posted: bool
    is_internal_transfer: bool
    short_id: str

    @computed_field
    @property
    def amount_display(self) -> str:
        sign = "+" if self.is_income else "-"
        return f"{sign}{self.amount:,.2f}"

    @computed_field
    @property
    def status_display(self) -> str:
        return "Posted" if self.is_posted else "Draft"

    @classmethod
    def from_transaction(cls, txn: Transaction) -> TransactionListItemDTO:
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


class TransactionListFilterDTO(BaseModel):
    """Filter and pagination parameters for listing transactions."""

    page: int = 1
    page_size: int = 50
    status_filter: Optional[str] = None
    iban_filter: Optional[str] = None
    show_drafts: bool = True
    exclude_transfers: Optional[bool] = None


class TransactionListResultDTO(BaseModel):
    """Result of listing transactions, with pagination and summary counts.

    ``total`` is the unfiltered transaction count for the user; ``filtered_count``
    is the count matching the active filters (and drives ``total_pages``).
    """

    transactions: list[TransactionListItemDTO] = []
    total: int = 0
    filtered_count: int = 0
    draft_count: int = 0
    posted_count: int = 0
    page: int = 1
    page_size: int = 50

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.filtered_count + self.page_size - 1) // self.page_size
