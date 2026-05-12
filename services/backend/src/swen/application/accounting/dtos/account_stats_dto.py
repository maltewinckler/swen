"""DTOs for account statistics queries."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class AccountStatsResult:
    """Result of account statistics query."""

    # Account identification
    account_id: UUID
    account_name: str
    account_number: str
    account_type: str  # 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE', 'EQUITY'
    currency: str

    # Balance information
    balance: Decimal
    balance_includes_drafts: bool

    # Transaction statistics
    transaction_count: int
    posted_count: int
    draft_count: int

    # Flow statistics (within the queried period)
    total_debits: Decimal
    total_credits: Decimal
    net_flow: Decimal  # debits - credits (for assets: positive = money in)

    # Activity timestamps
    first_transaction_date: Optional[date]
    last_transaction_date: Optional[date]

    # Period info
    period_days: Optional[int]
    period_start: Optional[date]
    period_end: Optional[date]

    def to_dict(self) -> dict:
        return {
            "account_id": str(self.account_id),
            "account_name": self.account_name,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "currency": self.currency,
            "balance": str(self.balance),
            "balance_includes_drafts": self.balance_includes_drafts,
            "transaction_count": self.transaction_count,
            "posted_count": self.posted_count,
            "draft_count": self.draft_count,
            "total_debits": str(self.total_debits),
            "total_credits": str(self.total_credits),
            "net_flow": str(self.net_flow),
            "first_transaction_date": (
                self.first_transaction_date.isoformat()
                if self.first_transaction_date
                else None
            ),
            "last_transaction_date": (
                self.last_transaction_date.isoformat()
                if self.last_transaction_date
                else None
            ),
            "period_days": self.period_days,
            "period_start": (
                self.period_start.isoformat() if self.period_start else None
            ),
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }
