"""Reconciliation schemas for API request/response models."""

from pydantic import ConfigDict

from swen.application.integration.dtos import (
    BankConnectionDetailsDTO,
    ReconciliationResultDTO,
)


class BankConnectionDetailsResponse(BankConnectionDetailsDTO):
    """Full details for a bank connection including all accounts."""

    model_config = ConfigDict(
        from_attributes=True,
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


class ReconciliationResponse(ReconciliationResultDTO):
    """Aggregated reconciliation result for all bank accounts."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
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
    )
