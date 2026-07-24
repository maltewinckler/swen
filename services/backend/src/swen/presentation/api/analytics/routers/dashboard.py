"""Dashboard router for financial summary endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from swen.application.analytics.queries import DashboardSummaryQuery
from swen.presentation.api.analytics.schemas.dashboard import (
    BalancesResponse,
    DashboardSummaryResponse,
    SpendingBreakdownResponse,
)
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()

# Type aliases for query parameters using Annotated (modern FastAPI pattern)
DaysFilter = Annotated[
    int | None,
    Query(ge=1, le=365, description="Days to look back (overrides month)"),
]
MonthFilter = Annotated[
    str | None,
    Query(pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format"),
]


@router.get(
    "/summary",
    summary="Get dashboard summary",
    responses={
        200: {"description": "Financial dashboard summary"},
    },
)
async def get_dashboard_summary(
    factory: RepoFactory,
    days: DaysFilter = None,
    month: MonthFilter = None,
) -> DashboardSummaryResponse:
    """
    Get a comprehensive financial dashboard summary.

    Includes:
    - Income and expense totals for the period
    - Current account balances
    - Spending breakdown by category
    - Recent transactions

    Either specify `days` to look back, or `month` for a specific month.
    If neither specified, defaults to current month.
    """
    query = DashboardSummaryQuery(
        account_repository=factory.account_repository(),
        transaction_repository=factory.transaction_repository(),
    )

    summary = await query.execute(
        days=days,
        month=month,
        show_drafts=True,
    )

    return DashboardSummaryResponse.model_validate(summary)


@router.get(
    "/spending",
    summary="Get spending breakdown",
    responses={
        200: {"description": "Spending breakdown by category"},
    },
)
async def get_spending_breakdown(
    factory: RepoFactory,
    days: DaysFilter = None,
    month: MonthFilter = None,
) -> SpendingBreakdownResponse:
    """
    Get spending breakdown by category.

    Shows how much was spent in each expense category.
    """
    query = DashboardSummaryQuery(
        account_repository=factory.account_repository(),
        transaction_repository=factory.transaction_repository(),
    )

    summary = await query.execute(
        days=days,
        month=month,
        show_drafts=False,  # Only posted transactions for spending
    )

    return SpendingBreakdownResponse(
        period_label=summary.period_label,
        total_spending=summary.total_expenses,
        categories=summary.category_spending,
    )


@router.get(
    "/balances",
    summary="Get account balances",
    responses={
        200: {"description": "Current account balances"},
    },
)
async def get_balances(
    factory: RepoFactory,
) -> BalancesResponse:
    """
    Get current balances for all asset accounts.

    Shows the current balance of each bank/asset account.
    """
    query = DashboardSummaryQuery(
        account_repository=factory.account_repository(),
        transaction_repository=factory.transaction_repository(),
    )

    # Get summary for balances (no date filter needed)
    summary = await query.execute(show_drafts=True)
    return BalancesResponse(balances=summary.account_balances)
