"""DTO for chart of accounts query result."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, computed_field

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account
    from swen.domain.integration.entities import AccountMapping


class AccountSummaryDTO(BaseModel):
    """Simplified account information for display."""

    model_config = ConfigDict(frozen=True)

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


class BankAccountDTO(BaseModel):
    """Bank account with mapping information for display."""

    model_config = ConfigDict(frozen=True)

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


class ChartOfAccountsDTO(BaseModel):
    """Chart of accounts organized by type in standard accounting order.

    This DTO provides accounts grouped by their type, following the
    standard accounting equation order: Assets, Liabilities, Equity,
    Income, Expenses.

    This structure is used for displaying the chart of accounts in
    various presentations (CLI, API, UI) without requiring the
    presentation layer to understand accounting organization.
    """

    assets: tuple[AccountSummaryDTO, ...] = ()
    liabilities: tuple[AccountSummaryDTO, ...] = ()
    equity: tuple[AccountSummaryDTO, ...] = ()
    income: tuple[AccountSummaryDTO, ...] = ()
    expenses: tuple[AccountSummaryDTO, ...] = ()

    @computed_field
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

    @computed_field
    @property
    def is_empty(self) -> bool:
        return self.total_count == 0

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
