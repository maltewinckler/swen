"""DiscoveredAccountDTO that carries full bank account data from discovery.

It is sent back to the frontend via API response to give the user the option
to rename the accounts. Then, it is sent back to the persistence command.
"""

from pydantic import BaseModel, ConfigDict, Field

from swen.application.banking.dtos import (
    BankDiscoveryResultDTO,
    BankInfoDTO,
    DiscoveredAccountDTO,
)


class TanMethodQueryRequest(BaseModel):
    """Request schema for querying available TAN methods (credentials read from DB)."""

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        pattern=r"^\d{8}$",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "12030000",
            },
        },
    )


# inherit from DTO to reuse fields and inject json schema
class BankInfoResponse(BankInfoDTO):
    """Response schema for bank lookup by BLZ."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "50031000",
                "name": "Triodos Bank N.V. Deutschland",
                "bic": "TRODDEF1",
                "organization": None,
                "is_fints_capable": True,
            },
        },
    )


class DiscoveredAccount(DiscoveredAccountDTO):
    """Full bank account data from discovery."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "iban": "DE89370400440532013000",
                "default_name": "DKB - Girokonto",
                "account_number": "0532013000",
                "account_holder": "Max Mustermann",
                "account_type": "Girokonto",
                "blz": "12030000",
                "bic": "BYLADEM1001",
                "bank_name": "DKB",
                "currency": "EUR",
                "balance": "1250.00",
                "balance_date": "2025-12-14T10:00:00",
            },
        },
    )


class BankDiscoveryResult(BankDiscoveryResultDTO):
    """Collection of discovered accounts for a bank."""

    accounts: list[DiscoveredAccount]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "blz": "12030000",
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "default_name": "DKB - Girokonto",
                        "account_number": "0532013000",
                        "account_holder": "Max Mustermann",
                        "account_type": "Girokonto",
                        "blz": "12030000",
                        "bank_name": "DKB",
                        "currency": "EUR",
                        "balance": "1250.00",
                    },
                ],
            },
        },
    )
