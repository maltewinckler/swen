"""Domain service for period-level financial summaries."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from swen.domain.accounting.entities import AccountType
from swen.domain.accounting.services.account_balance_service import (
    AccountBalanceService,
)

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction
    from swen.domain.accounting.entities import Account


# Very tiny scoped class that only carries this service's output.
class PeriodTotals(BaseModel):
    """Aggregated income, expenses and per-category spending for a period."""

    model_config = ConfigDict(frozen=True, validate_assignment=True)

    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    category_spending: dict[str, Decimal] = {}

    @property
    def net_income(self) -> Decimal:
        return self.total_income - self.total_expenses


class FinancialSummaryService:
    """Aggregates journal entries into period totals and asset balances.

    Encodes the double-entry rules the dashboard depends on: income accounts
    accrue on the credit side, expense accounts on the debit side, and only
    asset accounts contribute to reported balances.
    """

    @staticmethod
    def period_totals(transactions: list[Transaction]) -> PeriodTotals:
        """Sum income, expenses and per-category spending over transactions."""
        total_income = Decimal("0")
        total_expenses = Decimal("0")
        category_spending: dict[str, Decimal] = defaultdict(Decimal)

        for txn in transactions:
            for entry in txn.entries:
                account_type = entry.account.account_type
                if account_type == AccountType.INCOME:
                    if not entry.is_debit():
                        total_income += entry.credit.amount
                elif account_type == AccountType.EXPENSE and entry.is_debit():
                    total_expenses += entry.debit.amount
                    category_spending[entry.account.name] += entry.debit.amount

        return PeriodTotals(
            total_income=total_income,
            total_expenses=total_expenses,
            category_spending=dict(category_spending),
        )

    @staticmethod
    def asset_balances(
        accounts: list[Account],
        transactions: list[Transaction],
        balance_service: AccountBalanceService | None = None,
    ) -> list[tuple[Account, Decimal]]:
        """Return for every asset account (with drafts)."""
        service = balance_service or AccountBalanceService()

        balances: list[tuple[Account, Decimal]] = []
        for account in accounts:
            if account.account_type != AccountType.ASSET:
                continue
            account_txns = [t for t in transactions if t.involves_account(account)]
            balance = service.calculate_balance(
                account=account,
                transactions=account_txns,
                include_drafts=True,
            )
            balances.append((account, balance.amount))
        return balances
