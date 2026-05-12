"""DTOs for bank connection details with account reconciliation."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class BankAccountDetailDTO:
    """Details for a single bank account under a connection."""

    iban: str
    account_name: str
    account_type: str
    currency: str
    bank_balance: Decimal
    bank_balance_date: datetime | None
    bookkeeping_balance: Decimal
    discrepancy: Decimal
    is_reconciled: bool


@dataclass(frozen=True)
class BankConnectionDetailsDTO:
    """Full details for a bank connection including all accounts."""

    blz: str
    bank_name: str | None
    accounts: tuple[BankAccountDetailDTO, ...]
    total_accounts: int
    reconciled_count: int
    discrepancy_count: int
