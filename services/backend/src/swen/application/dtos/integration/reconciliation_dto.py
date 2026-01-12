"""DTO for bank account reconciliation results."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AccountReconciliationDTO:
    """Reconciliation result for a single bank account."""

    iban: str
    account_name: str
    accounting_account_id: str
    currency: str

    bank_balance: Decimal
    bank_balance_date: Optional[datetime]
    last_sync_at: Optional[datetime]

    bookkeeping_balance: Decimal

    discrepancy: Decimal
    is_reconciled: bool

    @property
    def discrepancy_abs(self) -> Decimal:
        return abs(self.discrepancy)

    def to_dict(self) -> dict:
        return {
            "iban": self.iban,
            "account_name": self.account_name,
            "accounting_account_id": self.accounting_account_id,
            "currency": self.currency,
            "bank_balance": str(self.bank_balance),
            "bank_balance_date": (
                self.bank_balance_date.isoformat() if self.bank_balance_date else None
            ),
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "bookkeeping_balance": str(self.bookkeeping_balance),
            "discrepancy": str(self.discrepancy),
            "is_reconciled": self.is_reconciled,
        }


@dataclass(frozen=True)
class ReconciliationResultDTO:
    """Aggregated reconciliation result for all bank accounts."""

    accounts: tuple[AccountReconciliationDTO, ...]
    total_accounts: int
    reconciled_count: int
    discrepancy_count: int

    @property
    def all_reconciled(self) -> bool:
        return self.discrepancy_count == 0

    @property
    def has_discrepancies(self) -> bool:
        return self.discrepancy_count > 0

    def to_dict(self) -> dict:
        return {
            "accounts": [acc.to_dict() for acc in self.accounts],
            "total_accounts": self.total_accounts,
            "reconciled_count": self.reconciled_count,
            "discrepancy_count": self.discrepancy_count,
            "all_reconciled": self.all_reconciled,
        }
