"""Application layer DTOs for transaction commands and responses.

These DTOs carry data from the presentation layer into the application layer.
They are plain Pydantic models with no domain type dependencies.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction


class TransactionEntryDTO(BaseModel):
    """Single journal entry for transaction commands.

    Uses plain Decimal (currency resolved later in the command).
    """

    account_id: UUID
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)


class SimpleTransactionToCreateDTO(BaseModel):
    """Application DTO for creating a simple two-entry transaction.

    The command resolves account numbers -> Account entities and
    Decimal amounts -> Money value objects internally.
    """

    model_config = ConfigDict(from_attributes=True)

    description: str = Field(min_length=1, max_length=500)
    amount: Decimal
    payment_account: str
    counter_account: str
    counterparty: Optional[str] = Field(None, max_length=200)
    date: Optional[datetime] = None
    auto_post: bool = False


class TransactionToCreateDTO(BaseModel):
    """Application DTO for creating a transaction.

    The command resolves account_ids -> Account entities and
    Decimal amounts -> Money value objects internally.
    """

    description: str = Field(min_length=1, max_length=500)
    entries: list[TransactionEntryDTO] = Field(min_length=2)
    counterparty: Optional[str] = Field(None, max_length=200)
    counterparty_iban: Optional[str] = None
    date: Optional[datetime] = None
    source: str = "manual"
    source_iban: Optional[str] = None
    is_internal_transfer: bool = False
    is_manual_entry: bool = False
    auto_post: bool = False


class JournalEntryDTO(BaseModel):
    """Single journal entry in a transaction response."""

    account_id: UUID
    account_name: str
    account_type: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    currency: str


class TransactionDTO(BaseModel):
    """Return DTO from create transaction command / detail query.

    Contains only primitive types -- no domain entity.
    The presentation layer maps this to TransactionResponse via model_validate.
    """

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str] = None
    counterparty_iban: Optional[str] = None
    bank_reference: Optional[str] = None
    source: str
    source_iban: Optional[str] = None
    is_posted: bool
    is_internal_transfer: bool
    created_at: datetime
    entries: list[JournalEntryDTO]
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_transaction(cls, txn: "Transaction") -> "TransactionDTO":
        """Build TransactionDTO from a domain Transaction entity."""
        entries: list[JournalEntryDTO] = []
        for entry in txn.entries:
            account = entry.account
            if entry.is_debit():
                debit_val: Optional[Decimal] = entry.debit.amount
                credit_val: Optional[Decimal] = None
                currency = entry.debit.currency.code
            else:
                debit_val = None
                credit_val = entry.credit.amount
                currency = entry.credit.currency.code
            entries.append(
                JournalEntryDTO(
                    account_id=account.id,
                    account_name=account.name,
                    account_type=account.account_type.value,
                    debit=debit_val,
                    credit=credit_val,
                    currency=currency,
                ),
            )
        return cls(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            counterparty=txn.counterparty,
            counterparty_iban=txn.counterparty_iban,
            bank_reference=txn.get_metadata_raw("bank_reference") or None,
            source=txn.source.value,
            source_iban=txn.source_iban,
            is_posted=txn.is_posted,
            is_internal_transfer=txn.is_internal_transfer,
            created_at=txn.created_at,
            entries=entries,
            metadata=txn.metadata_raw,
        )
