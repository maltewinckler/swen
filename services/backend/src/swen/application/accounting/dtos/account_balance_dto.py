"""DTO for account balance query result."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class AccountBalanceDTO:
    """Account balance information for presentation layer."""

    account_id: str
    account_name: str
    account_number: Optional[str]
    account_type: str
    balance: Decimal
    currency: str
    balance_date: Optional[date]
    is_active: bool
    # Hierarchy fields
    is_parent: bool = False
    parent_id: Optional[str] = None
    includes_children: bool = False

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "balance": str(self.balance),
            "currency": self.currency,
            "balance_date": (
                self.balance_date.isoformat() if self.balance_date else None
            ),
            "is_active": self.is_active,
            "is_parent": self.is_parent,
            "parent_id": self.parent_id,
            "includes_children": self.includes_children,
        }

    @property
    def formatted_balance(self) -> str:
        return f"{self.balance:.2f} {self.currency}"
