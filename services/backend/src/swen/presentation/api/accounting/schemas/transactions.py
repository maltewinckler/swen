"""Transaction schemas for API request/response models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from swen.application.accounting.dtos import (
    JournalEntryDTO,
    TransactionDTO,
    TransactionListItemDTO,
)


# inherit from DTO to reuse fields and inject json schema
class JournalEntryResponse(JournalEntryDTO):
    """Response schema for a journal entry (one side of double-entry).

    In double-entry bookkeeping, each transaction has at least two entries
    that balance (total debits = total credits).
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "DKB Checking Account",
                "account_type": "asset",
                "debit": None,
                "credit": "45.99",
                "currency": "EUR",
            },
        },
    )


# inherit from DTO to reuse fields and inject json schema
class TransactionResponse(TransactionDTO):
    """Response schema for full transaction data with journal entries.

    Each transaction contains balanced journal entries following
    double-entry bookkeeping principles.
    """

    entries: list[JournalEntryResponse]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "counterparty": "REWE",
                "counterparty_iban": "DE89370400440532013000",
                "bank_reference": None,
                "source": "bank_import",
                "source_iban": "DE75512108001245126199",
                "is_posted": True,
                "is_internal_transfer": False,
                "created_at": "2024-12-05T15:00:00Z",
                "entries": [
                    {
                        "account_id": "660e8400-e29b-41d4-a716-446655440001",
                        "account_name": "Groceries",
                        "account_type": "expense",
                        "debit": "45.99",
                        "credit": None,
                        "currency": "EUR",
                    },
                    {
                        "account_id": "550e8400-e29b-41d4-a716-446655440000",
                        "account_name": "DKB Checking Account",
                        "account_type": "asset",
                        "debit": None,
                        "credit": "45.99",
                        "currency": "EUR",
                    },
                ],
                "metadata": {
                    "ai_resolution": {
                        "suggested_counter_account_name": "Groceries",
                        "confidence": 0.95,
                        "reasoning": "REWE is a German supermarket chain",
                        "model": "qwen2.5:3b",
                    },
                },
            },
        },
    )


class TransactionListItemResponse(TransactionListItemDTO):
    """Response schema for transaction in list view (simplified for display)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "short_id": "550e8400",
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "counterparty": "REWE",
                "counter_account": "Groceries",
                "debit_account": "Groceries",
                "credit_account": "DKB Girokonto",
                "amount": "45.99",
                "currency": "EUR",
                "is_income": False,
                "is_posted": True,
                "is_internal_transfer": False,
            },
        },
    )


class TransactionListResponse(BaseModel):
    """Response schema for transaction listing with pagination and summary counts."""

    transactions: list[TransactionListItemResponse]
    total: int
    filtered_count: int
    draft_count: int
    posted_count: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transactions": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "short_id": "550e8400",
                        "date": "2024-12-05T14:30:00Z",
                        "description": "REWE Supermarket",
                        "counterparty": "REWE",
                        "counter_account": "Groceries",
                        "amount": "45.99",
                        "currency": "EUR",
                        "is_income": False,
                        "is_posted": True,
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "short_id": "660e8400",
                        "date": "2024-12-01T09:00:00Z",
                        "description": "Salary December",
                        "counterparty": "ACME Corp",
                        "counter_account": "Salary",
                        "amount": "3500.00",
                        "currency": "EUR",
                        "is_income": True,
                        "is_posted": True,
                    },
                ],
                "total": 120,
                "filtered_count": 95,
                "draft_count": 5,
                "posted_count": 115,
                "page": 1,
                "page_size": 50,
                "total_pages": 2,
            },
        },
    )


class JournalEntryCreateRequest(BaseModel):
    """Request schema for a journal entry when creating a transaction.

    Each transaction needs at least two balanced entries (debits = credits).
    """

    account_id: UUID
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "debit": "45.99",
                "credit": "0",
            },
        },
    )


class TransactionCreateRequest(BaseModel):
    """Request schema for creating a manual transaction.

    Transactions follow double-entry bookkeeping: total debits must equal total credits.

    **Simple expense example** (buying groceries for €45.99):
    - Entry 1: Debit €45.99 to "Groceries" (expense account)
    - Entry 2: Credit €45.99 from "Checking" (asset account)

    **Simple income example** (receiving salary of €3000):
    - Entry 1: Debit €3000 to "Checking" (asset account)
    - Entry 2: Credit €3000 from "Salary" (income account)
    """

    date: datetime
    description: str = Field(min_length=1, max_length=500)
    entries: list[JournalEntryCreateRequest] = Field(min_length=2)
    counterparty: Optional[str] = Field(None, max_length=200)
    auto_post: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "entries": [
                    {
                        "account_id": "660e8400-e29b-41d4-a716-446655440001",
                        "debit": "45.99",
                        "credit": "0",
                    },
                    {
                        "account_id": "550e8400-e29b-41d4-a716-446655440000",
                        "debit": "0",
                        "credit": "45.99",
                    },
                ],
                "counterparty": "REWE",
                "auto_post": True,
            },
        },
    )


class SimpleTransactionToCreateRequest(BaseModel):
    """Simplified request for creating a two-entry transaction.

    Use this when you want to record an expense or income with explicit
    account selection (dropdown-based in the UI).

    - **Negative amount** = expense (money leaving)
    - **Positive amount** = income (money coming in)

    The caller must specify both accounts:
    - ``payment_account``: the asset or liability account (e.g. bank account)
    - ``counter_account``: the expense or income account
    """

    date: datetime
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal
    payment_account: str = Field(min_length=1, max_length=20)
    counter_account: str = Field(min_length=1, max_length=20)
    counterparty: Optional[str] = Field(None, max_length=200)
    auto_post: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "amount": "-45.99",
                "payment_account": "1100",
                "counter_account": "4200",
                "counterparty": "REWE",
                "auto_post": True,
            },
        },
    )


class TransactionUpdateRequest(BaseModel):
    """Request schema for updating/editing an existing transaction.

    All fields are optional - only provided fields will be updated.

    **Entry Editing**:
    Use `entries` for full replacement of journal entries. This is for
    advanced editing like splitting transactions or correcting amounts.

    **Counter Account Change**:
    Use `counter_account_id` for simple re-categorization (swapping the
    expense/income account while keeping the same amount).

    Note: `entries` and `counter_account_id` are mutually exclusive.
    """

    description: Optional[str] = Field(None, min_length=1, max_length=500)
    counterparty: Optional[str] = Field(None, max_length=200)
    counter_account_id: Optional[UUID] = None
    entries: Optional[list[JournalEntryCreateRequest]] = Field(None, min_length=1)
    repost: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Simple re-categorization",
                    "value": {
                        "counter_account_id": "660e8400-e29b-41d4-a716-446655440001",
                        "repost": True,
                    },
                },
                {
                    "summary": "Update description and counterparty",
                    "value": {
                        "description": "Updated description",
                        "counterparty": "New Store Name",
                    },
                },
                {
                    "summary": "Replace entries (split transaction)",
                    "value": {
                        "entries": [
                            {
                                "account_id": "550e8400-e29b-41d4-a716-446655440001",
                                "debit": "30.00",
                                "credit": "0",
                            },
                            {
                                "account_id": "550e8400-e29b-41d4-a716-446655440002",
                                "debit": "20.00",
                                "credit": "0",
                            },
                            {
                                "account_id": "550e8400-e29b-41d4-a716-446655440003",
                                "debit": "0",
                                "credit": "50.00",
                            },
                        ],
                        "repost": True,
                    },
                },
            ],
        },
    )


# ═══════════════════════════════════════════════════════════════
#           Reclassify / Bulk-Post schemas
# ═══════════════════════════════════════════════════════════════


class ReclassifyDraftsRequest(BaseModel):
    """Request schema for reclassifying draft transactions via ML."""

    transaction_ids: Optional[list[UUID]] = Field(
        None,
        description="Specific draft transaction IDs to reclassify",
    )
    reclassify_all: bool = Field(
        default=False,
        description="Reclassify all draft bank-import transactions",
    )
    only_fallback: bool = Field(
        default=False,
        description="Only reclassify drafts on fallback accounts (Sonstiges / "
        "Sonstige Einnahmen)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Reclassify all uncategorised drafts",
                    "value": {
                        "reclassify_all": True,
                        "only_fallback": True,
                    },
                },
                {
                    "summary": "Reclassify specific transactions",
                    "value": {
                        "transaction_ids": [
                            "550e8400-e29b-41d4-a716-446655440000",
                        ],
                    },
                },
            ],
        },
    )


class BulkPostRequest(BaseModel):
    """Request schema for posting multiple draft transactions."""

    transaction_ids: Optional[list[UUID]] = Field(
        None,
        description="Specific draft transaction IDs to post",
    )
    post_all_drafts: bool = Field(
        default=False,
        description="Post all remaining draft transactions",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_all_drafts": True,
            },
        },
    )


class BulkPostResponse(BaseModel):
    """Response schema for bulk-posting transactions."""

    posted_count: int
    transaction_ids: list[UUID]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "posted_count": 2,
                "transaction_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "660e8400-e29b-41d4-a716-446655440001",
                ],
            },
        },
    )
