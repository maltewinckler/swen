"""DiscoveredAccountDTO that carries full bank account data from discovery.

It is sent back to the frontend via API response to give the user the option
to rename the accounts. Then, it is sent back to the persistence command.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TanMethodQueryRequest(BaseModel):
    """Request schema for querying available TAN methods (credentials read from DB)."""

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        pattern=r"^\d{8}$",
        description="Bank code (BLZ) - exactly 8 digits",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "12030000",
            },
        },
    )


class BankInfo(BaseModel):
    """Bank Info Fast API Schema."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    blz: str
    name: str
    bic: Optional[str]
    organization: Optional[str] = None
    is_fints_capable: bool = True


class DiscoveredAccount(BaseModel):
    """Full bank account data from discovery."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    # Display info
    iban: str
    default_name: str

    account_number: str
    account_holder: str
    account_type: str
    blz: str
    bic: Optional[str]
    bank_name: Optional[str]
    currency: str = "EUR"
    balance: Optional[str] = None
    balance_date: Optional[str] = None


class BankDiscoveryResult(BaseModel):
    """Collection of discovered accounts for a bank."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    blz: str
    accounts: list[DiscoveredAccount]
