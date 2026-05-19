"""DTO that has discovered bank account data with user injections.

The DiscoveredBankAccountsCollectionDTO carries the data coming from the bank
and the user can inject custom names for import into swen DB.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from swen.application.banking.dtos.discovered_accounts_dto import DiscoveredAccountDTO


class BankAccountToImportDTO(DiscoveredAccountDTO):
    """Bank account data for import with user-injected custom name."""

    custom_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[\w \t\-\.(),]*$",  # whitelist
        description="User-injected custom name",
    )


class ImportedBankAccountDTO(BankAccountToImportDTO):
    """Bank account data for import with user-injected custom name and import result."""

    accounting_account_id: Optional[UUID] = Field(None, description="Accounting ID")


class SetupBankRequestDTO(BaseModel):
    """DTO for bank account import with user-injected custom names."""

    blz: str
    accounts: list[BankAccountToImportDTO] = Field(..., min_length=1)


class SetupBankResponseDTO(BaseModel):
    """DTO for bank account import response."""

    blz: str
    imported_accounts: list[ImportedBankAccountDTO] = Field(..., min_length=1)
    # success flag and status messages
    success: bool
    message: str
    warning: Optional[str]
