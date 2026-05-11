"""DTO that has discovered bank account data with user injections.

The DiscoveredBankAccountsCollectionDTO carries the data coming from the bank
and the user can inject custom names for import into swen DB.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from swen.application.dtos.banking.discovered_accounts_dto import DiscoveredAccountDTO


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

    blz: str = Field(..., description="Bank BLZ")
    accounts: list[BankAccountToImportDTO] = Field(
        ...,
        min_length=1,
        description="Accounts to import",
    )


class SetupBankResponseDTO(BaseModel):
    """DTO for bank account import response."""

    blz: str
    imported_accounts: list[ImportedBankAccountDTO] = Field(
        ...,
        min_length=1,
        description="List of accounts that were imported",
    )

    success: bool = Field(..., description="Whether the import was successful")
    message: str = Field(..., description="Status message")
    warning: Optional[str] = Field(None, description="Warning message if any")
