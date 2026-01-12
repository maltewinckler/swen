"""Account schemas for API request/response models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChartTemplateEnum(str, Enum):
    """Available chart of accounts templates.

    MINIMAL: Simple categories for basic personal finance (~15 accounts)
    """

    MINIMAL = "minimal"


# Import ParentAction from application layer (business logic owns the enum)
from swen.application.commands.accounting import ParentAction


class InitChartRequest(BaseModel):
    """Request schema for initializing chart of accounts."""

    template: ChartTemplateEnum = Field(
        default=ChartTemplateEnum.MINIMAL,
        description="Chart template to use: 'minimal' for simple categories (~15 accounts)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Minimal (recommended for personal use)",
                    "value": {"template": "minimal"},
                },
            ],
        },
    }


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

    model_config = {
        "json_schema_extra": {
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
    }


class AccountResponse(BaseModel):
    """Response schema for account data."""

    id: UUID = Field(..., description="Account unique identifier")
    name: str = Field(
        ..., description="Account name (e.g., 'Checking Account', 'Groceries')"
    )
    account_number: str = Field(
        ..., description="Chart of accounts number (e.g., '1200', '6001')"
    )
    account_type: str = Field(
        ..., description="Account type: asset, liability, equity, income, expense"
    )
    description: Optional[str] = Field(
        None,
        description="Description with typical transactions/merchants for AI classification",  # NOQA: E501
    )
    iban: Optional[str] = Field(
        None,
        description="IBAN for bank accounts or external accounts with IBAN mapping",
    )
    currency: str = Field(
        ..., description="ISO 4217 currency code (e.g., 'EUR', 'USD')"
    )
    is_active: bool = Field(
        ..., description="Whether account is active (inactive = soft deleted)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    parent_id: Optional[UUID] = Field(
        None,
        description="Parent account ID for sub-accounts (null if top-level account)",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
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
    }


class AccountWithBalanceResponse(AccountResponse):
    """Account response with current balance."""

    balance: Decimal = Field(
        ...,
        description="Current balance (positive for assets, negative for liabilities)",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DKB Checking Account",
                "account_number": "1200",
                "account_type": "asset",
                "description": None,
                "currency": "EUR",
                "is_active": True,
                "created_at": "2024-12-01T09:00:00Z",
                "balance": "2543.67",
            },
        },
    }


class AccountCreateRequest(BaseModel):
    """Request schema for creating an account."""

    name: str = Field(..., min_length=1, max_length=255, description="Account name")
    account_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Account number",
    )
    account_type: str = Field(
        ...,
        description="Account type: asset, liability, equity, income, expense",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description with examples for AI classification (e.g., 'Supermarkets: REWE, Lidl, EDEKA')",  # NOQA: E501
    )
    currency: str = Field(default="EUR", description="Currency code (default: EUR)")
    parent_id: Optional[UUID] = Field(
        None,
        description="Parent account ID to create this as a sub-account (must be same type)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
                "description": "Supermarkets, groceries: REWE, Lidl, EDEKA, Aldi",
                "currency": "EUR",
                "parent_id": None,
            },
        },
    }


class AccountUpdateRequest(BaseModel):
    """Request schema for updating an account."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="New account name",
    )
    account_number: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="New account number/code (must be unique per user)",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description with examples for AI classification",
    )
    parent_id: Optional[UUID] = Field(
        None,
        description="Parent account ID (required when parent_action is 'set')",
    )
    parent_action: ParentAction = Field(
        default=ParentAction.KEEP,
        description=(
            "Action for parent relationship: "
            "'keep' = don't change (default), "
            "'set' = set parent to parent_id, "
            "'remove' = make top-level account"
        ),
    )

    model_config = {
        "json_schema_extra": {
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
    }


class AccountListResponse(BaseModel):
    """Response schema for account listing."""

    accounts: list[AccountResponse] = Field(
        ..., description="List of accounts matching filters"
    )
    total: int = Field(..., description="Total number of accounts")
    by_type: dict[str, int] = Field(..., description="Breakdown of accounts by type")

    model_config = {
        "json_schema_extra": {
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
    }


class BankAccountResponse(BaseModel):
    """Response schema for bank account with mapping info."""

    id: UUID = Field(..., description="Account ID in the system")
    name: str = Field(..., description="Account name (can be customized)")
    account_number: str = Field(..., description="Chart of accounts number")
    iban: str = Field(
        ..., description="Bank account IBAN (used for transaction matching)"
    )
    currency: str = Field(..., description="Account currency code")
    is_active: bool = Field(..., description="Whether account is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DKB Checking Account",
                "account_number": "1200",
                "iban": "DE89370400440532013000",
                "currency": "EUR",
                "is_active": True,
            },
        },
    }


class BankAccountListResponse(BaseModel):
    """Response schema for bank account listing."""

    accounts: list[BankAccountResponse] = Field(
        ..., description="Bank accounts imported from bank connections"
    )
    total: int = Field(..., description="Total number of bank accounts")

    model_config = {
        "json_schema_extra": {
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
    }


class BankAccountRenameRequest(BaseModel):
    """Request schema for renaming a bank account."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New display name for the account",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Main Checking Account",
            },
        },
    }


class AccountStatsResponse(BaseModel):
    """Response schema for account statistics.

    Provides comprehensive statistics for a single account including
    balance, transaction counts, and flow data.
    """

    # Account identification
    account_id: UUID = Field(..., description="Account unique identifier")
    account_name: str = Field(..., description="Account display name")
    account_number: str = Field(..., description="Chart of accounts number")
    account_type: str = Field(..., description="Account type (asset, liability, etc.)")
    currency: str = Field(..., description="ISO 4217 currency code")

    # Balance information
    balance: Decimal = Field(..., description="Current balance")
    balance_includes_drafts: bool = Field(
        ...,
        description="Whether balance includes draft transactions",
    )

    # Transaction statistics
    transaction_count: int = Field(..., description="Total transactions in period")
    posted_count: int = Field(..., description="Posted transactions")
    draft_count: int = Field(..., description="Draft (pending) transactions")

    # Flow statistics
    total_debits: Decimal = Field(..., description="Total debit amount in period")
    total_credits: Decimal = Field(..., description="Total credit amount in period")
    net_flow: Decimal = Field(
        ...,
        description="Net flow (debits - credits; for assets: positive = money in)",
    )

    # Activity timestamps
    first_transaction_date: Optional[str] = Field(
        None,
        description="Date of first transaction (ISO format)",
    )
    last_transaction_date: Optional[str] = Field(
        None,
        description="Date of most recent transaction (ISO format)",
    )

    # Period info
    period_days: Optional[int] = Field(
        None,
        description="Number of days in the stats period (null = all-time)",
    )
    period_start: Optional[str] = Field(
        None,
        description="Start of the stats period (ISO date)",
    )
    period_end: Optional[str] = Field(
        None,
        description="End of the stats period (ISO date)",
    )

    model_config = {
        "json_schema_extra": {
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
    }


class AccountReconciliationResponse(BaseModel):
    """Reconciliation result for a single bank account."""

    iban: str = Field(..., description="Bank account IBAN")
    account_name: str = Field(..., description="Accounting account name")
    accounting_account_id: str = Field(..., description="Accounting account UUID")
    currency: str = Field(..., description="Account currency")

    bank_balance: str = Field(
        ..., description="Balance reported by bank (from last sync)"
    )
    bank_balance_date: Optional[str] = Field(
        None, description="Date of bank balance (ISO format)"
    )
    last_sync_at: Optional[str] = Field(
        None, description="Last sync timestamp (ISO format)"
    )

    bookkeeping_balance: str = Field(
        ..., description="Balance calculated from accounting transactions"
    )
    discrepancy: str = Field(
        ..., description="Difference between bank and bookkeeping balances"
    )
    is_reconciled: bool = Field(
        ..., description="Whether balances match (within tolerance)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "iban": "DE89370400440532013000",
                "account_name": "DKB Checking Account",
                "accounting_account_id": "550e8400-e29b-41d4-a716-446655440000",
                "currency": "EUR",
                "bank_balance": "2543.67",
                "bank_balance_date": "2024-12-10T10:30:00Z",
                "last_sync_at": "2024-12-10T10:30:00Z",
                "bookkeeping_balance": "2543.67",
                "discrepancy": "0.00",
                "is_reconciled": True,
            },
        },
    }


class ReconciliationResponse(BaseModel):
    """Aggregated reconciliation result for all bank accounts."""

    accounts: list[AccountReconciliationResponse] = Field(
        ..., description="Reconciliation results per bank account"
    )
    total_accounts: int = Field(..., description="Total number of bank accounts")
    reconciled_count: int = Field(
        ..., description="Number of accounts with matching balances"
    )
    discrepancy_count: int = Field(
        ..., description="Number of accounts with discrepancies"
    )
    all_reconciled: bool = Field(
        ..., description="Whether all accounts are reconciled"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "account_name": "DKB Checking Account",
                        "accounting_account_id": "550e8400-e29b-41d4-a716-446655440000",
                        "currency": "EUR",
                        "bank_balance": "2543.67",
                        "bank_balance_date": "2024-12-10T10:30:00Z",
                        "last_sync_at": "2024-12-10T10:30:00Z",
                        "bookkeeping_balance": "2543.67",
                        "discrepancy": "0.00",
                        "is_reconciled": True,
                    },
                ],
                "total_accounts": 1,
                "reconciled_count": 1,
                "discrepancy_count": 0,
                "all_reconciled": True,
            },
        },
    }
