"""Mapping schemas for API request/response models.

Schemas for bank account to ledger account mappings.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExternalAccountType(str, Enum):
    """Account types allowed for external accounts.

    ASSET: Bank accounts, stock portfolios, foreign banks
    LIABILITY: Credit cards, loans, mortgages
    """

    ASSET = "asset"
    LIABILITY = "liability"


class AccountMappingResponse(BaseModel):
    """Response schema for a bank account mapping."""

    id: UUID
    iban: str
    account_name: str
    accounting_account_id: UUID
    accounting_account_name: Optional[str] = None
    accounting_account_number: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "iban": "DE89370400440532013000",
                "account_name": "Girokonto",
                "accounting_account_id": "660e8400-e29b-41d4-a716-446655440001",
                "accounting_account_name": "DKB Checking",
                "accounting_account_number": "1000",
                "created_at": "2024-01-01T00:00:00+00:00",
            }
        },
    )


class AccountMappingListResponse(BaseModel):
    """Response for listing bank account mappings."""

    mappings: list[AccountMappingResponse]
    count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "mappings": [],
                "count": 0,
            }
        },
    )


class ExternalAccountCreateRequest(BaseModel):
    """Request to create a mapping for an external bank account.

    Use this for accounts at banks that don't offer FinTS access.

    For ASSET accounts (default):
    - Transfers are tracked as internal transfers (Asset ↔ Asset)
    - Useful for stock portfolios, foreign banks

    For LIABILITY accounts:
    - Payments are tracked as liability payments
    - Useful for credit cards, loans without FinTS access
    """

    iban: str = Field(..., min_length=15, max_length=34)
    name: str = Field(..., min_length=1, max_length=255)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    account_type: ExternalAccountType = Field(default=ExternalAccountType.ASSET)
    reconcile: bool = Field(default=True)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "summary": "External bank account (asset)",
                    "value": {
                        "iban": "DE51120700700756557355",
                        "name": "Deutsche Bank Depot",
                        "currency": "EUR",
                        "account_type": "asset",
                        "reconcile": True,
                    },
                },
                {
                    "summary": "Credit card (liability)",
                    "value": {
                        "iban": "DE89370400440532013000",
                        "name": "Norwegian VISA",
                        "currency": "EUR",
                        "account_type": "liability",
                        "reconcile": False,
                    },
                },
            ]
        },
    )


class ExternalAccountCreateResponse(BaseModel):
    """Response after creating an external account mapping."""

    mapping: AccountMappingResponse
    transactions_reconciled: int
    already_existed: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "mapping": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "iban": "DE51120700700756557355",
                    "account_name": "Deutsche Bank Depot",
                    "accounting_account_id": "660e8400-e29b-41d4-a716-446655440001",
                    "accounting_account_name": "Deutsche Bank Depot",
                    "accounting_account_number": "DE51120700700756557355",
                    "created_at": "2024-01-01T00:00:00+00:00",
                },
                "transactions_reconciled": 5,
                "already_existed": False,
            }
        },
    )
