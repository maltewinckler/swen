"""Analytics read port (report-like interface).

This is the *application* read-side contract. It is intentionally report-like:
each method corresponds to a user-facing report / chart.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from swen.application.dtos.analytics import (
    CategoryTimeSeriesResult,
    IncomeBreakdownResult,
    MonthComparisonResult,
    SpendingBreakdownResult,
    TimeSeriesResult,
    TopExpensesResult,
)


class AnalyticsReadPort(Protocol):
    """Report-like analytics read interface."""

    async def spending_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> CategoryTimeSeriesResult:
        """Monthly spending (expense accounts) by category over time."""
        ...

    async def single_account_spending_over_time(
        self,
        *,
        account_id: UUID,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        """Monthly spending for a single expense account over time.

        Used for drill-down views where user selects a specific expense
        category from a dropdown.
        """
        ...

    async def income_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        """Monthly income totals over time."""
        ...

    async def net_income_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        """Monthly net income (income - expenses) over time."""
        ...

    async def savings_rate_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        """Monthly savings rate (%) over time."""
        ...

    async def net_worth_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = True,
    ) -> TimeSeriesResult:
        """Monthly net worth (assets - liabilities) over time."""
        ...

    async def balance_history_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = True,
    ) -> CategoryTimeSeriesResult:
        """Monthly balances by asset account over time."""
        ...

    async def spending_breakdown(
        self,
        *,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> SpendingBreakdownResult:
        """Spending breakdown (pie) for a month or rolling window."""
        ...

    async def income_breakdown(
        self,
        *,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> IncomeBreakdownResult:
        """Income breakdown (pie) for a month or rolling window."""
        ...

    async def month_comparison(
        self,
        *,
        month: str | None = None,
        include_drafts: bool = False,
    ) -> MonthComparisonResult:
        """Compare current vs previous month (income/spending/net + categories)."""
        ...

    async def top_expenses(
        self,
        *,
        months: int = 3,
        top_n: int = 10,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TopExpensesResult:
        """Top expense categories over a period."""
        ...
