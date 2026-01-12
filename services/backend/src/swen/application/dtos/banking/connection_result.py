"""DTO for bank connection command result."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AccountInfo:
    """Information about an imported account."""

    iban: str
    account_name: str
    account_number: str
    bank_code: str
    balance_amount: str
    balance_currency: str
    accounting_account_id: str


@dataclass(frozen=True)
class ConnectionResult:
    """Result of bank connection command execution."""

    success: bool
    connected_at: datetime
    bank_code: str
    accounts_imported: list[AccountInfo]
    error_message: Optional[str] = None
    warning_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "connected_at": self.connected_at.isoformat(),
            "bank_code": self.bank_code,
            "accounts_imported": [
                {
                    "iban": acc.iban,
                    "account_name": acc.account_name,
                    "account_number": acc.account_number,
                    "bank_code": acc.bank_code,
                    "balance_amount": acc.balance_amount,
                    "balance_currency": acc.balance_currency,
                    "accounting_account_id": acc.accounting_account_id,
                }
                for acc in self.accounts_imported
            ],
            "error_message": self.error_message,
            "warning_message": self.warning_message,
        }

    @property
    def accounts_count(self) -> int:
        return len(self.accounts_imported)
