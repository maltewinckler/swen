"""DiscoveredAccountDTO that carries full bank account data from discovery.

It is sent back to the frontend via API response to give the user the option
to rename the accounts. Then, it is sent back to the persistence command.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BankInfoDTO(BaseModel):
    """Basic bank info for display during discovery."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    blz: str
    name: str
    bic: Optional[str]
    organization: Optional[str] = None
    is_fints_capable: bool = True


class DiscoveredAccountDTO(BaseModel):
    """Full bank account data from discovery."""

    model_config = ConfigDict(frozen=True)

    # Display info
    iban: str
    default_name: str
    account_number: str
    account_holder: str
    account_type: str
    blz: str
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    currency: str = "EUR"
    balance: Optional[str] = None
    balance_date: Optional[str] = None


class BankDiscoveryResultDTO(BaseModel):
    """Collection of discovered accounts for a bank."""

    model_config = ConfigDict(frozen=True)

    blz: str
    accounts: list[DiscoveredAccountDTO]
