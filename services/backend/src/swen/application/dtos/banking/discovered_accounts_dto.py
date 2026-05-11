"""DiscoveredAccountDTO that carries full bank account data from discovery.

It is sent back to the frontend via API response to give the user the option
to rename the accounts. Then, it is sent back to the persistence command.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredAccountDTO(BaseModel):
    """Full bank account data from discovery."""

    model_config = ConfigDict(frozen=True)

    # Display info
    iban: str = Field(..., description="Bank account IBAN")
    default_name: str = Field(
        ...,
        description="Default name generated for the account (e.g., 'DKB - Girokonto')",
    )

    account_number: str = Field(..., description="Local account number")
    account_holder: str = Field(..., description="Name of account holder")
    account_type: str = Field(..., description="Type of account (e.g., 'Girokonto')")
    blz: str = Field(..., description="Bank code (BLZ)")
    bic: Optional[str] = Field(None, description="Bank BIC code")
    bank_name: Optional[str] = Field(None, description="Name of the bank")
    currency: str = Field(default="EUR", description="Account currency")
    balance: Optional[str] = Field(None, description="Current balance")
    balance_date: Optional[str] = Field(None, description="When balance was fetched")


class DiscoveredAccountsCollectionDTO(BaseModel):
    """Collection of discovered accounts for a bank."""

    model_config = ConfigDict(frozen=True)

    blz: str = Field(..., description="Bank BLZ")
    accounts: list[DiscoveredAccountDTO] = Field(
        ...,
        description="List of discovered bank accounts (pass back to /setup to import)",
    )
