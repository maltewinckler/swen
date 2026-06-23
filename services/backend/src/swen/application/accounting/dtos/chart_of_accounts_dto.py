"""DTO for chart of accounts query result."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account
    from swen.domain.integration.entities import AccountMapping


@dataclass(frozen=True)
class AccountSummaryDTO:
    """Simplified account information for display."""

    id: str
    name: str
    account_number: str
    account_type: str
    currency: str
    is_active: bool
    description: Optional[str] = None
    iban: Optional[str] = None
    created_at: Optional[datetime] = None
    parent_id: Optional[str] = None

    @classmethod
    def from_entity(cls, account: Account) -> AccountSummaryDTO:
        return cls(
            id=str(account.id),
            name=account.name,
            account_number=account.account_number or "",
            account_type=account.account_type.value,
            currency=account.default_currency.code,
            is_active=account.is_active,
            description=account.description,
            iban=account.iban,
            created_at=account.created_at,
            parent_id=str(account.parent_id) if account.parent_id else None,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "currency": self.currency,
            "is_active": self.is_active,
            "description": self.description,
            "iban": self.iban,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "parent_id": self.parent_id,
        }


@dataclass(frozen=True)
class BankAccountDTO:
    """Bank account with mapping information for display."""

    id: str
    name: str
    account_number: str
    iban: str
    currency: str
    is_active: bool

    @classmethod
    def from_entities(
        cls,
        account: Account,
        mapping: AccountMapping,
    ) -> BankAccountDTO:
        return cls(
            id=str(account.id),
            name=account.name,
            account_number=account.account_number or "",
            iban=mapping.iban,
            currency=account.default_currency.code,
            is_active=account.is_active,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "account_number": self.account_number,
            "iban": self.iban,
            "currency": self.currency,
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class ChartOfAccountsDTO:
    """Chart of accounts organized by type in standard accounting order.

    This DTO provides accounts grouped by their type, following the
    standard accounting equation order: Assets, Liabilities, Equity,
    Income, Expenses.

    This structure is used for displaying the chart of accounts in
    various presentations (CLI, API, UI) without requiring the
    presentation layer to understand accounting organization.
    """

    assets: tuple[AccountSummaryDTO, ...] = field(default_factory=tuple)
    liabilities: tuple[AccountSummaryDTO, ...] = field(default_factory=tuple)
    equity: tuple[AccountSummaryDTO, ...] = field(default_factory=tuple)
    income: tuple[AccountSummaryDTO, ...] = field(default_factory=tuple)
    expenses: tuple[AccountSummaryDTO, ...] = field(default_factory=tuple)

    @property
    def total_count(self) -> int:
        """Total number of accounts across all types."""
        return (
            len(self.assets)
            + len(self.liabilities)
            + len(self.equity)
            + len(self.income)
            + len(self.expenses)
        )

    @property
    def is_empty(self) -> bool:
        return self.total_count == 0

    def to_dict(self) -> dict:
        return {
            "assets": [a.to_dict() for a in self.assets],
            "liabilities": [a.to_dict() for a in self.liabilities],
            "equity": [a.to_dict() for a in self.equity],
            "income": [a.to_dict() for a in self.income],
            "expenses": [a.to_dict() for a in self.expenses],
            "total_count": self.total_count,
        }

    def iter_by_type(self):
        groups = [
            ("Asset", self.assets),
            ("Liability", self.liabilities),
            ("Equity", self.equity),
            ("Income", self.income),
            ("Expense", self.expenses),
        ]
        for type_name, accounts in groups:
            if accounts:
                yield type_name, accounts
