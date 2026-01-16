"""Dashboard router for financial summary endpoints."""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from swen.application.dtos.accounting import TransactionListItemDTO
from swen.application.queries import DashboardSummaryQuery
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.dashboard import (
    AccountBalanceResponse,
    BalancesResponse,
    CategorySpendingResponse,
    DashboardSummaryResponse,
    RecentTransactionResponse,
    SpendingBreakdownResponse,
)

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


def _transaction_to_recent_response(
    txn_dto: TransactionListItemDTO,
) -> RecentTransactionResponse:
    """Convert TransactionListItemDTO to dashboard's recent transaction response."""
    return RecentTransactionResponse(
        id=txn_dto.id,
        date=txn_dto.date,
        description=txn_dto.description,
        amount=txn_dto.amount,
        currency=txn_dto.currency,
        is_income=txn_dto.is_income,
    )


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

    # Convert account balances
    account_balances = [
        AccountBalanceResponse(
            id=account.id,
            name=account.name,
            balance=balance,
            currency=account.default_currency.code,
        )
        for account, balance in summary.account_balances.items()
    ]

    # Convert category spending (sorting is presentation concern)
    category_spending = [
        CategorySpendingResponse(
            category=category,
            amount=amount,
        )
        for category, amount in sorted(
            summary.category_spending.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    # Convert recent transactions using existing DTO
    # The DTO encapsulates the business logic for determining amount/direction
    recent_transactions = [
        _transaction_to_recent_response(TransactionListItemDTO.from_transaction(txn))
        for txn in summary.recent_transactions[:10]
    ]

    return DashboardSummaryResponse(
        period_label=summary.period_label,
        total_income=summary.total_income,
        total_expenses=summary.total_expenses,
        net_income=summary.total_income - summary.total_expenses,
        account_balances=account_balances,
        category_spending=category_spending,
        recent_transactions=recent_transactions,
        draft_count=summary.draft_count,
        posted_count=summary.posted_count,
    )


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

    # Convert and sort categories (sorting is presentation concern)
    categories = [
        CategorySpendingResponse(
            category=category,
            amount=amount,
        )
        for category, amount in sorted(
            summary.category_spending.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    return SpendingBreakdownResponse(
        period_label=summary.period_label,
        total_spending=summary.total_expenses,
        categories=categories,
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

    balances = [
        AccountBalanceResponse(
            id=account.id,
            name=account.name,
            balance=balance,
            currency=account.default_currency.code,
        )
        for account, balance in summary.account_balances.items()
    ]

    # Sum total assets (simple aggregation is acceptable in presentation layer)
    total_assets = sum(summary.account_balances.values(), Decimal(0))

    return BalancesResponse(
        balances=balances,
        total_assets=total_assets,
    )
