"""Transaction schemas for API request/response models."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JournalEntryResponse(BaseModel):
    """Response schema for a journal entry (one side of double-entry).

    In double-entry bookkeeping, each transaction has at least two entries
    that balance (total debits = total credits).
    """

    account_id: UUID
    account_name: str
    account_type: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    currency: str

    model_config = ConfigDict(
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


class TransactionResponse(BaseModel):
    """Response schema for full transaction data with journal entries.

    Each transaction contains balanced journal entries following
    double-entry bookkeeping principles.
    """

    id: UUID
    date: datetime
    description: str
    counterparty: Optional[str] = None
    counterparty_iban: Optional[str] = None
    source: str
    source_iban: Optional[str] = None
    is_posted: bool
    is_internal_transfer: bool
    created_at: datetime
    entries: list[JournalEntryResponse]
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "counterparty": "REWE",
                "counterparty_iban": "DE89370400440532013000",
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


class TransactionListItemResponse(BaseModel):
    """Response schema for transaction in list view (simplified for display)."""

    id: UUID
    short_id: str
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

    model_config = ConfigDict(
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
    """Response schema for transaction listing with summary counts."""

    transactions: list[TransactionListItemResponse]
    total: int
    draft_count: int
    posted_count: int

    model_config = ConfigDict(
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
                "total": 2,
                "draft_count": 0,
                "posted_count": 2,
            },
        },
    )


class TransactionPostRequest(BaseModel):
    """Request schema for posting a transaction."""

    # No body needed, just the ID in path


class JournalEntryRequest(BaseModel):
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
    entries: list[JournalEntryRequest] = Field(min_length=2)
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


class TransactionCreateSimpleRequest(BaseModel):
    """Simplified request for creating a transaction with automatic account resolution.

    Use this when you just want to record an expense or income without
    worrying about double-entry details.

    - **Negative amount** = expense (money leaving)
    - **Positive amount** = income (money coming in)

    The system will automatically:
    - Find your default asset account (or use the one specified)
    - Find an appropriate expense/income category
    - Create the balanced journal entries
    """

    date: datetime
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal
    asset_account: Optional[str] = None
    category_account: Optional[str] = None
    counterparty: Optional[str] = Field(None, max_length=200)
    auto_post: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "amount": "-45.99",
                "asset_account": None,
                "category_account": "6001",
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

    **Category Change**:
    Use `category_account_id` for simple re-categorization (swapping the
    expense/income account while keeping the same amount).

    Note: `entries` and `category_account_id` are mutually exclusive.
    """

    description: Optional[str] = Field(None, min_length=1, max_length=500)
    counterparty: Optional[str] = Field(None, max_length=200)
    category_account_id: Optional[UUID] = None
    entries: Optional[list[JournalEntryRequest]] = Field(None, min_length=1)
    repost: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Simple re-categorization",
                    "value": {
                        "category_account_id": "660e8400-e29b-41d4-a716-446655440001",
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


class TransactionFilterParams(BaseModel):
    """Query parameters for transaction filtering."""

    days: int = Field(default=30, ge=1, le=365)
    limit: int = Field(default=50, ge=1, le=500)
    status: Optional[str] = None
    account_number: Optional[str] = None
    exclude_transfers: Optional[bool] = None
    source: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "days": 30,
                "limit": 50,
                "status": "posted",
                "account_number": None,
                "exclude_transfers": True,
                "source": None,
            },
        },
    )
