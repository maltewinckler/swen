"""Account schemas for API request/response models."""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from swen.application.accounting.commands import ParentAction
from swen.application.accounting.dtos import (
    AccountStatsDTO,
    AccountSummaryDTO,
    BankAccountDTO,
)
from swen.application.accounting.queries import AccountListDTO


class ChartTemplateEnum(str, Enum):
    """Available chart of accounts templates.

    MINIMAL: Simple categories for basic personal finance (~15 accounts)
    """

    MINIMAL = "minimal"


class InitChartRequest(BaseModel):
    """Request schema for initializing chart of accounts."""

    template: ChartTemplateEnum = Field(
        default=ChartTemplateEnum.MINIMAL,
        description="Chart template to use: 'minimal' for simple categories",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Minimal (recommended for personal use)",
                    "value": {"template": "minimal"},
                },
            ],
        },
    )


class InitChartResponse(BaseModel):
    """Response schema for chart initialization."""

    message: str = Field(..., description="Success message")
    skipped: bool = Field(..., description="True if accounts already existed")
    accounts_created: int = Field(..., description="Number of accounts created")
    template: Optional[str] = Field(None, description="Template used (if created)")
    by_type: Optional[dict[str, int]] = Field(
        None,
        description="Breakdown of created accounts by type",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "New accounts created",
                    "value": {
                        "message": "Created 15 default accounts",
                        "skipped": False,
                        "accounts_created": 15,
                        "template": "minimal",
                        "by_type": {
                            "income": 2,
                            "expense": 12,
                            "equity": 1,
                            "asset": 0,
                            "liability": 0,
                        },
                    },
                },
                {
                    "summary": "Already exists",
                    "value": {
                        "message": "Chart of accounts already exists",
                        "skipped": True,
                        "accounts_created": 0,
                    },
                },
            ],
        },
    )


class InitEssentialsResponse(BaseModel):
    """Response schema for essential accounts initialization."""

    message: str
    skipped: bool
    accounts_created: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Essential accounts created",
                    "value": {
                        "message": "Created 3 essential accounts",
                        "skipped": False,
                        "accounts_created": 3,
                    },
                },
                {
                    "summary": "Already exist",
                    "value": {
                        "message": "Essential accounts already exist",
                        "skipped": True,
                        "accounts_created": 0,
                    },
                },
            ],
        },
    )


class AccountSummaryResponse(AccountSummaryDTO):
    """Response schema for account data."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DKB Checking Account",
                "account_number": "1200",
                "account_type": "asset",
                "description": None,
                "iban": "DE89370400440532013000",
                "currency": "EUR",
                "is_active": True,
                "created_at": "2024-12-01T09:00:00Z",
                "parent_id": None,
            },
        },
    )


class AccountCreateRequest(BaseModel):
    """Request schema for creating an account."""

    name: str = Field(..., min_length=1, max_length=255, description="Account name")
    account_number: str = Field(..., min_length=1, max_length=50)
    account_type: str
    description: Optional[str] = Field(default=None, max_length=500)
    currency: str = Field(default="EUR")
    parent_id: Optional[UUID] = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
                "description": "Supermarkets, groceries: REWE, Lidl, EDEKA, Aldi",
                "currency": "EUR",
                "parent_id": None,
            },
        },
    )


class AccountUpdateRequest(BaseModel):
    """Request schema for updating an account."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[UUID] = Field(default=None)
    parent_action: ParentAction = Field(default=ParentAction.KEEP)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Update name only (keep parent unchanged)",
                    "value": {"name": "Main Checking Account"},
                },
                {
                    "summary": "Update description for AI",
                    "value": {
                        "description": "Supermarkets, groceries: REWE, Lidl, EDEKA",
                    },
                },
                {
                    "summary": "Set parent account (make sub-account)",
                    "value": {
                        "parent_id": "550e8400-e29b-41d4-a716-446655440000",
                        "parent_action": "set",
                    },
                },
                {
                    "summary": "Remove parent (make top-level)",
                    "value": {
                        "parent_action": "remove",
                    },
                },
            ],
        },
    )


class AccountListResponse(AccountListDTO):
    """Response schema for account listing."""

    accounts: list[AccountSummaryResponse]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "DKB Checking Account",
                        "account_number": "1200",
                        "account_type": "asset",
                        "currency": "EUR",
                        "is_active": True,
                        "created_at": "2024-12-01T09:00:00Z",
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Groceries",
                        "account_number": "6001",
                        "account_type": "expense",
                        "currency": "EUR",
                        "is_active": True,
                        "created_at": "2024-12-01T09:00:00Z",
                    },
                ],
                "total": 2,
                "by_type": {"asset": 1, "expense": 1},
            },
        },
    )


class BankAccountResponse(BankAccountDTO):
    """Response schema for bank account with mapping info."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DKB Checking Account",
                "account_number": "1200",
                "iban": "DE89370400440532013000",
                "currency": "EUR",
                "is_active": True,
            },
        },
    )


class BankAccountListResponse(BaseModel):
    """Response schema for bank account listing."""

    accounts: list[BankAccountResponse]

    @computed_field
    @property
    def total(self) -> int:
        """Total number of bank accounts."""
        return len(self.accounts)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "DKB Checking Account",
                        "account_number": "1200",
                        "iban": "DE89370400440532013000",
                        "currency": "EUR",
                        "is_active": True,
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Triodos Savings",
                        "account_number": "1210",
                        "iban": "DE91100000000123456789",
                        "currency": "EUR",
                        "is_active": True,
                    },
                ],
                "total": 2,
            },
        },
    )


class BankAccountRenameRequest(BaseModel):
    """Request schema for renaming a bank account."""

    name: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main Checking Account",
            },
        },
    )


class AccountStatsResponse(AccountStatsDTO):
    """Response schema for account statistics."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "DKB Checking Account",
                "account_number": "1200",
                "account_type": "asset",
                "currency": "EUR",
                "balance": "2543.67",
                "balance_includes_drafts": True,
                "transaction_count": 42,
                "posted_count": 40,
                "draft_count": 2,
                "total_debits": "5000.00",
                "total_credits": "7543.67",
                "net_flow": "2543.67",
                "first_transaction_date": "2024-01-15",
                "last_transaction_date": "2024-12-05",
                "period_days": 30,
                "period_start": "2024-11-05",
                "period_end": "2024-12-05",
            },
        },
    )
