"""DTO for transaction sync command result."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class SyncResult:
    """Result of transaction sync command execution.

    This DTO provides structured information about the transaction
    sync and import process for the presentation layer.
    """

    success: bool
    synced_at: datetime
    iban: str
    start_date: date
    end_date: date
    transactions_fetched: int
    transactions_imported: int
    transactions_skipped: int
    transactions_failed: int
    transactions_reconciled: int = 0
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    opening_balance_created: bool = False
    opening_balance_amount: Optional[Decimal] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "synced_at": self.synced_at.isoformat(),
            "iban": self.iban,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "transactions_fetched": self.transactions_fetched,
            "transactions_imported": self.transactions_imported,
            "transactions_skipped": self.transactions_skipped,
            "transactions_failed": self.transactions_failed,
            "transactions_reconciled": self.transactions_reconciled,
            "error_message": self.error_message,
            "warning_message": self.warning_message,
            "opening_balance_created": self.opening_balance_created,
            "opening_balance_amount": (
                float(self.opening_balance_amount)
                if self.opening_balance_amount is not None
                else None
            ),
        }

    @property
    def success_rate(self) -> float:
        if self.transactions_fetched == 0:
            return 0.0
        return (self.transactions_imported / self.transactions_fetched) * 100
