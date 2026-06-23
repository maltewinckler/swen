"""DTOs for bank connection details with account reconciliation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BankAccountDetailDTO(BaseModel):
    """Details for a single bank account under a connection."""

    model_config = ConfigDict(frozen=True)

    iban: str
    account_name: str
    account_type: str
    currency: str
    bank_balance: Decimal
    bank_balance_date: datetime | None
    bookkeeping_balance: Decimal
    discrepancy: Decimal
    is_reconciled: bool


class BankConnectionDetailsDTO(BaseModel):
    """Full details for a bank connection including all accounts."""

    model_config = ConfigDict(frozen=True)

    blz: str
    bank_name: str | None
    accounts: tuple[BankAccountDetailDTO, ...]
    total_accounts: int
    reconciled_count: int
    discrepancy_count: int
