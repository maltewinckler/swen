"""Credentials schemas for API request/response models."""

from pydantic import BaseModel, ConfigDict

from swen.application.banking.dtos import (
    BankAccountToImportDTO,
    SetupBankResponseDTO,
    TANMethodInfoDTO,
    TANMethodsResultDTO,
)


class SetupBankRequest(BaseModel):
    """Request body for bank setup with discovered accounts and custom names."""

    # cannot fully inherit from DTO because it has blz which is in api header not body
    accounts: list[BankAccountToImportDTO]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "default_name": "DKB - Girokonto",
                        "custom_name": "Hebelkonto",
                        "account_number": "0532013000",
                        "account_holder": "Max Mustermann",
                        "account_type": "Girokonto",
                        "blz": "12030000",
                        "bank_name": "DKB",
                        "currency": "EUR",
                        "balance": "1250.00",
                        "balance_date": "2025-12-14T10:00:00",
                    },
                ],
            },
        },
    )


class SetupBankResponse(SetupBankResponseDTO):
    """Response for bank setup (connect + import accounts)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "success": True,
                "blz": "12030000",
                "imported_accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "default_name": "DKB - Girokonto",
                        "custom_name": "Hebelkonto",
                        "account_number": "0532013000",
                        "account_holder": "Max Mustermann",
                        "account_type": "Girokonto",
                        "blz": "12030000",
                        "bic": "BYLADEM1001",
                        "bank_name": "DKB",
                        "currency": "EUR",
                        "balance": "1250.00",
                        "balance_date": "2025-12-14T10:00:00",
                        "accounting_account_id": "550e8400-e29b-41d4-a716-446655440000",
                    },
                ],
                "message": "Successfully imported 1 bank account(s)",
                "warning": None,
            },
        },
    )


class TANMethodResponse(TANMethodInfoDTO):
    """Information about a TAN authentication method supported by a bank."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "code": "940",
                "name": "DKB App",
                "method_type": "decoupled",
                "is_decoupled": True,
                "technical_id": "SealOne",
                "zka_id": "Decoupled",
                "zka_version": None,
                "max_tan_length": None,
                "decoupled_max_polls": 999,
                "decoupled_first_poll_delay": 5,
                "decoupled_poll_interval": 2,
                "supports_cancel": False,
                "supports_multiple_tan": False,
            },
        },
    )


class TANMethodsResponse(TANMethodsResultDTO):
    """Response for TAN methods query."""

    tan_methods: list[TANMethodResponse]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "blz": "12030000",
                "bank_name": "Deutsche Kreditbank Berlin (DKB) AG",
                "tan_methods": [
                    {
                        "code": "940",
                        "name": "DKB App",
                        "method_type": "decoupled",
                        "is_decoupled": True,
                        "technical_id": "SealOne",
                        "zka_id": "Decoupled",
                        "decoupled_max_polls": 999,
                        "decoupled_first_poll_delay": 5,
                        "decoupled_poll_interval": 2,
                    },
                ],
                "default_method": "940",
            },
        },
    )
