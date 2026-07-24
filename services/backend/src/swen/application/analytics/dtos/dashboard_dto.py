"""DTOs for the dashboard summary query."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from swen.domain.accounting.services import TransactionAnalyzer

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction


class AccountBalanceDTO(BaseModel):
    """Current balance of a single asset account."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    balance: Decimal
    currency: str


class CategorySpendingDTO(BaseModel):
    """Total spending in one expense category."""

    model_config = ConfigDict(frozen=True)

    category: str
    amount: Decimal
    currency: str = "EUR"


class RecentTransactionDTO(BaseModel):
    """Simplified transaction for the dashboard's recent-activity list."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    date: datetime
    description: str
    amount: Decimal
    currency: str
    is_income: bool

    @classmethod
    def from_transaction(cls, txn: Transaction) -> RecentTransactionDTO:
        return cls(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            amount=TransactionAnalyzer.payment_amount(txn),
            currency=TransactionAnalyzer.payment_currency(txn),
            is_income=TransactionAnalyzer.is_income(txn),
        )


class DashboardSummaryDTO(BaseModel):
    """Aggregated financial overview for the dashboard."""

    model_config = ConfigDict(frozen=True)

    period_label: str
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    account_balances: list[AccountBalanceDTO] = []
    category_spending: list[CategorySpendingDTO] = []
    recent_transactions: list[RecentTransactionDTO] = []
    draft_count: int = 0
    posted_count: int = 0
