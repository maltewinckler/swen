"""Reconciliation schemas for API request/response models."""

from typing import Optional

from pydantic import ConfigDict

from swen.application.integration.dtos import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)


# inherit from DTO to reuse fields and inject json schema
class BankAccountDetailResponse(BankAccountDetailDTO):
    """Details for a single bank account under a connection."""

    # we have to override types from Decimal/datetime to str for serialization.
    bank_balance: str
    bank_balance_date: Optional[str] = None
    bookkeeping_balance: str
    discrepancy: str


class BankConnectionDetailsResponse(BankConnectionDetailsDTO):
    """Full details for a bank connection including all accounts."""

    accounts: list[BankAccountDetailResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "50031000",
                "bank_name": "Triodos Bank",
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "account_name": "Girokonto Triodos",
                        "account_type": "Girokonto",
                        "currency": "EUR",
                        "bank_balance": "14255.12",
                        "bank_balance_date": "2025-12-10T00:00:00",
                        "bookkeeping_balance": "14255.12",
                        "discrepancy": "0.00",
                        "is_reconciled": True,
                    },
                ],
                "total_accounts": 1,
                "reconciled_count": 1,
                "discrepancy_count": 0,
            },
        },
    )
