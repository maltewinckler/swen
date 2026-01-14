"""Credentials schemas for API request/response models."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class CredentialResponse(BaseModel):
    """Response schema for credential metadata (no sensitive data)."""

    credential_id: str = Field(..., description="Unique credential identifier")
    blz: str = Field(..., description="Bank code (BLZ) - 8 digits")
    label: str = Field(..., description="User-friendly label (typically bank name)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "credential_id": "cred_abc123def456",
                "blz": "50031000",
                "label": "Triodos Bank N.V. Deutschland",
            },
        },
    )

class CredentialListResponse(BaseModel):
    """Response schema for credential listing."""

    credentials: list[CredentialResponse] = Field(
        ...,
        description="List of stored credentials (sensitive data never exposed)",
    )
    total: int = Field(..., description="Total number of stored credentials")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credentials": [
                    {
                        "credential_id": "cred_abc123def456",
                        "blz": "50031000",
                        "label": "Triodos Bank N.V. Deutschland",
                    },
                    {
                        "credential_id": "cred_xyz789ghi012",
                        "blz": "12030000",
                        "label": "DKB Deutsche Kreditbank",
                    },
                ],
                "total": 2,
            },
        },
    )

class CredentialCreateRequest(BaseModel):
    """Request schema for storing new credentials."""

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        pattern=r"^\d{8}$",
        description="Bank code (BLZ) - exactly 8 digits",
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Bank login username/ID",
    )
    pin: str = Field(..., min_length=1, max_length=100, description="Bank PIN")
    tan_method: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="TAN method code (e.g., '946' for SecureGo plus)",
    )
    tan_medium: Optional[str] = Field(
        default=None,
        max_length=100,
        description="TAN medium/device name (e.g., 'SecureGo'). Optional for most TAN methods.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "50031000",
                "username": "my_username",
                "pin": "my_secret_pin",
                "tan_method": "946",
                "tan_medium": None,
            },
        },
    )

class CredentialCreateResponse(BaseModel):
    """Response schema after storing credentials."""

    credential_id: str = Field(..., description="ID of the newly stored credential")
    blz: str = Field(..., description="Bank code (BLZ)")
    label: str = Field(..., description="Bank name (auto-resolved from BLZ)")
    message: str = Field(..., description="Success confirmation message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credential_id": "cred_abc123def456",
                "blz": "50031000",
                "label": "Triodos Bank N.V. Deutschland",
                "message": "Credentials stored successfully",
            },
        },
    )

class BankLookupResponse(BaseModel):
    """Response schema for bank lookup by BLZ."""

    blz: str = Field(..., description="Bank code (BLZ)")
    name: str = Field(..., description="Bank name")
    bic: Optional[str] = Field(None, description="Bank BIC code")
    city: Optional[str] = Field(None, description="Bank city")
    endpoint_url: str = Field(..., description="FinTS endpoint URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "50031000",
                "name": "Triodos Bank N.V. Deutschland",
                "bic": "TRODDEF1",
                "city": "Frankfurt am Main",
                "endpoint_url": "https://banking-dkb.s-fints-pt-dkb.de/fints30",
            },
        },
    )

class ConnectionTestResponse(BaseModel):
    """Response schema for connection test."""

    success: bool = Field(..., description="Whether connection test succeeded")
    accounts_found: int = Field(
        ...,
        description="Number of bank accounts found at this bank",
    )
    message: str = Field(..., description="Human-readable result message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "accounts_found": 2,
                "message": "Connection successful! Found 2 account(s).",
            },
        },
    )

class AccountImportInfo(BaseModel):
    """Info about an imported bank account."""

    iban: str = Field(..., description="Bank account IBAN")
    account_name: str = Field(..., description="Name assigned to the account")
    balance: Optional[str] = Field(None, description="Current balance")
    currency: str = Field(default="EUR", description="Account currency")
    accounting_account_id: Optional[UUID] = Field(
        None,
        description="Linked accounting account UUID",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "iban": "DE89370400440532013000",
                "account_name": "DKB - Girokonto",
                "balance": "1250.00",
                "currency": "EUR",
                "accounting_account_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        },
    )

class BankAccountData(BaseModel):
    """Bank account data for import (subset of DiscoveredAccount for setup request)."""

    iban: str = Field(..., description="Bank account IBAN")
    account_number: str = Field(..., description="Local account number")
    account_holder: str = Field(..., description="Name of account holder")
    account_type: str = Field(..., description="Type of account (e.g., 'Girokonto')")
    blz: str = Field(..., description="Bank code (BLZ)")
    bic: Optional[str] = Field(None, description="Bank BIC code")
    bank_name: Optional[str] = Field(None, description="Name of the bank")
    currency: str = Field(default="EUR", description="Account currency")
    balance: Optional[str] = Field(None, description="Current balance")
    balance_date: Optional[str] = Field(None, description="When balance was fetched")

class SetupBankRequest(BaseModel):
    """Request body for bank setup with discovered accounts and custom names."""

    accounts: Optional[list[BankAccountData]] = Field(
        None,
        description="Bank accounts from /discover-accounts endpoint. "
        "If provided, skips bank connection (no TAN needed). "
        "If not provided, connects to bank to fetch accounts.",
    )
    account_names: Optional[dict[str, str]] = Field(
        None,
        description="Optional mapping of IBAN -> custom account name. "
        "If not provided for an IBAN, a default name is generated.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "account_number": "0532013000",
                        "account_holder": "Max Mustermann",
                        "account_type": "Girokonto",
                        "blz": "12030000",
                        "bank_name": "DKB",
                        "currency": "EUR",
                        "balance": "1250.00",
                    },
                ],
                "account_names": {
                    "DE89370400440532013000": "My Main Checking",
                },
            },
        },
    )

class SetupBankResponse(BaseModel):
    """Response for bank setup (connect + import accounts)."""

    success: bool = Field(..., description="Whether setup completed successfully")
    bank_code: str = Field(..., description="Bank BLZ")
    accounts_imported: list[AccountImportInfo] = Field(
        ...,
        description="List of imported bank accounts",
    )
    message: str = Field(..., description="Status message")
    warning: Optional[str] = Field(None, description="Warning message if any")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "bank_code": "12030000",
                "accounts_imported": [
                    {
                        "iban": "DE89370400440532013000",
                        "account_name": "DKB - Girokonto",
                        "balance": "1250.00",
                        "currency": "EUR",
                        "accounting_account_id": "550e8400-e29b-41d4-a716-446655440000",
                    },
                ],
                "message": "Successfully imported 1 bank account(s)",
                "warning": None,
            },
        },
    )

class DiscoveredAccount(BaseModel):
    """Full bank account data from discovery (passed back to setup to avoid re-fetching)."""

    # Display info
    iban: str = Field(..., description="Bank account IBAN")
    default_name: str = Field(
        ...,
        description="Default name generated for the account (e.g., 'DKB - Girokonto')",
    )

    # Full bank account data (needed for import)
    account_number: str = Field(..., description="Local account number")
    account_holder: str = Field(..., description="Name of account holder")
    account_type: str = Field(..., description="Type of account (e.g., 'Girokonto')")
    blz: str = Field(..., description="Bank code (BLZ)")
    bic: Optional[str] = Field(None, description="Bank BIC code")
    bank_name: Optional[str] = Field(None, description="Name of the bank")
    currency: str = Field(default="EUR", description="Account currency")
    balance: Optional[str] = Field(None, description="Current balance")
    balance_date: Optional[str] = Field(None, description="When balance was fetched")

    model_config = ConfigDict(
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

class DiscoverAccountsResponse(BaseModel):
    """Response for account discovery (connect + list accounts without importing)."""

    blz: str = Field(..., description="Bank BLZ")
    bank_name: str = Field(..., description="Bank name")
    accounts: list[DiscoveredAccount] = Field(
        ...,
        description="List of discovered bank accounts (pass back to /setup to import)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "12030000",
                "bank_name": "Deutsche Kreditbank Berlin (DKB) AG",
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

TANMethodTypeStr = Literal[
    "decoupled",
    "push",
    "sms",
    "chiptan",
    "photo_tan",
    "manual",
    "unknown",
]

class TANMethodQueryRequest(BaseModel):
    """Request schema for querying available TAN methods."""

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        pattern=r"^\d{8}$",
        description="Bank code (BLZ) - exactly 8 digits",
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Bank login username/ID",
    )
    pin: str = Field(..., min_length=1, max_length=100, description="Bank PIN")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "12030000",
                "username": "my_username",
                "pin": "my_secret_pin",
            },
        },
    )

class TANMethodResponse(BaseModel):
    """Information about a TAN authentication method supported by a bank."""

    code: str = Field(..., description="Security function code (e.g., '946', '972')")
    name: str = Field(..., description="Human-readable name (e.g., 'DKB App')")
    method_type: TANMethodTypeStr = Field(
        ...,
        description="Category: decoupled, push, sms, chiptan, photo_tan, manual",
    )
    is_decoupled: bool = Field(
        ...,
        description="True if app-based approval (no code entry needed)",
    )
    technical_id: Optional[str] = Field(
        None,
        description="Technical ID (e.g., 'HHD1.4', 'SealOne')",
    )
    zka_id: Optional[str] = Field(None, description="ZKA standard identifier")
    zka_version: Optional[str] = Field(None, description="ZKA standard version")
    max_tan_length: Optional[int] = Field(None, description="Maximum TAN input length")
    decoupled_max_polls: Optional[int] = Field(
        None,
        description="Max status polls for decoupled methods",
    )
    decoupled_first_poll_delay: Optional[int] = Field(
        None,
        description="Seconds before first poll",
    )
    decoupled_poll_interval: Optional[int] = Field(
        None,
        description="Seconds between polls",
    )
    supports_cancel: bool = Field(
        default=False,
        description="Whether cancellation is supported",
    )
    supports_multiple_tan: bool = Field(
        default=False,
        description="Whether multiple TANs are supported",
    )

    model_config = ConfigDict(
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

class TANMethodsResponse(BaseModel):
    """Response for TAN methods query."""

    blz: str = Field(..., description="Bank code (BLZ)")
    bank_name: str = Field(..., description="Bank name")
    tan_methods: list[TANMethodResponse] = Field(
        ...,
        description="List of available TAN methods",
    )
    default_method: Optional[str] = Field(
        None,
        description="Recommended TAN method code (usually first decoupled method)",
    )

    model_config = ConfigDict(
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

# Bank Connection Details schemas

class BankAccountDetailResponse(BaseModel):
    """Details for a single bank account under a connection."""

    iban: str = Field(description="Account IBAN")
    account_name: str = Field(description="Account name in bookkeeping")
    account_type: str = Field(description="Account type (e.g., Girokonto)")
    currency: str = Field(description="Account currency")
    bank_balance: str = Field(description="Balance reported by bank")
    bank_balance_date: Optional[str] = Field(
        None,
        description="When bank balance was fetched",
    )
    bookkeeping_balance: str = Field(description="Calculated bookkeeping balance")
    discrepancy: str = Field(description="Difference between bank and bookkeeping")
    is_reconciled: bool = Field(description="Whether balances match")

class BankConnectionDetailsResponse(BaseModel):
    """Full details for a bank connection including all accounts."""

    blz: str = Field(description="Bank code (BLZ)")
    bank_name: Optional[str] = Field(None, description="Bank name")
    accounts: list[BankAccountDetailResponse] = Field(
        description="All accounts under this connection",
    )
    total_accounts: int = Field(description="Number of accounts")
    reconciled_count: int = Field(description="Number of reconciled accounts")
    discrepancy_count: int = Field(description="Number of accounts with discrepancies")

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
