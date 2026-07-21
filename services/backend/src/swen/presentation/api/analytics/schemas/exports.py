"""Pydantic schemas for data export endpoints."""

from pydantic import BaseModel, ConfigDict, computed_field

from swen.application.analytics.dtos import (
    AccountExportDTO,
    ExportResultDTO,
    TransactionExportDTO,
)

# TransactionExportDTO/AccountExportDTO/MappingExportDTO are referenced directly
# below, not wrapped in a *Response subclass -- none of them is ever returned
# standalone from an endpoint, so per the inheritance-pattern rule in AGENTS.md
# there's nothing to override; they flow through model_validate unchanged.


class TransactionExportListResponse(BaseModel):
    """Response for transaction export."""

    transactions: list[TransactionExportDTO]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.transactions)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transactions": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "date": "2024-12-05",
                        "description": "REWE Supermarket",
                        "counterparty": "REWE",
                        "counterparty_iban": "DE89370400440532013000",
                        "source": "bank_import",
                        "source_iban": "DE75512108001245126199",
                        "is_internal_transfer": False,
                        "amount": 45.99,
                        "currency": "EUR",
                        "debit_account": "4200 - Lebensmittel",
                        "credit_account": "1000 - DKB Checking",
                        "status": "posted",
                        "metadata": "{}",
                        "created_at": "2024-12-05T15:00:00+00:00",
                    },
                ],
                "count": 1,
            }
        }
    )


class AccountExportListResponse(BaseModel):
    """Response for account export."""

    accounts: list[AccountExportDTO]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.accounts)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "account_number": "4200",
                        "name": "Lebensmittel",
                        "type": "expense",
                        "currency": "EUR",
                        "is_active": True,
                        "parent_id": "",
                        "created_at": "2024-01-01T00:00:00+00:00",
                    },
                ],
                "count": 1,
            }
        }
    )


# inherit from DTO to reuse fields and inject json schema
class FullExportResponse(ExportResultDTO):
    """Response for full data export (backup)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transactions": [],
                "accounts": [],
                "mappings": [],
                "transaction_count": 0,
                "account_count": 0,
                "mapping_count": 0,
            }
        },
    )
