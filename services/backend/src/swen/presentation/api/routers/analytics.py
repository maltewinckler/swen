"""Analytics router for financial visualization endpoints.

Provides aggregated data for charts and dashboards, including
time series data for trends and breakdowns for distributions.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from swen.application.queries import (
    BalanceHistoryQuery,
    IncomeBreakdownQuery,
    IncomeOverTimeQuery,
    MonthComparisonQuery,
    NetIncomeOverTimeQuery,
    NetWorthQuery,
    SankeyQuery,
    SavingsRateQuery,
    SingleAccountSpendingQuery,
    SpendingBreakdownQuery,
    SpendingOverTimeQuery,
    TopExpensesQuery,
)
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.analytics import (
    BreakdownItemResponse,
    CategoryComparisonResponse,
    CategoryDataResponse,
    CategoryTimeSeriesResponse,
    IncomeBreakdownResponse,
    MonthComparisonResponse,
    SankeyLinkResponse,
    SankeyNodeResponse,
    SankeyResponse,
    SpendingBreakdownResponse,
    TimeSeriesDataPointResponse,
    TimeSeriesResponse,
    TopExpenseItemResponse,
    TopExpensesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MonthsParam = Annotated[
    int,
    Query(ge=1, le=60, description="Number of months to look back"),
]
EndMonthParam = Annotated[
    str | None,
    Query(pattern=r"^\d{4}-\d{2}$", description="End month (YYYY-MM format)"),
]
MonthParam = Annotated[
    str | None,
    Query(pattern=r"^\d{4}-\d{2}$", description="Specific month (YYYY-MM format)"),
]
DaysParam = Annotated[
    int | None,
    Query(ge=1, le=365, description="Days to look back (overrides month)"),
]
IncludeDraftsParam = Annotated[
    bool,
    Query(description="Include draft (non-posted) transactions"),
]
TopNParam = Annotated[
    int,
    Query(ge=1, le=50, description="Number of top items to return"),
]

@router.get(
    "/spending/over-time",
    summary="Get spending over time by category",
    responses={
        200: {"description": "Monthly spending breakdown by expense category"},
    },
)
async def get_spending_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> CategoryTimeSeriesResponse:
    """
    Get monthly spending breakdown by expense category.

    Returns time series data suitable for:
    - Stacked bar charts (spending by category per month)
    - Multi-line charts (one line per expense category)
    - Area charts showing spending trends

    Categories are sorted by total spending (highest first).
    """
    query = SpendingOverTimeQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return CategoryTimeSeriesResponse(
        data_points=[
            CategoryDataResponse(
                period=dp.period,
                period_label=dp.period_label,
                categories=dp.categories,
                total=dp.total,
            )
            for dp in result.data_points
        ],
        categories=result.categories,
        currency=result.currency,
        totals_by_category=result.totals_by_category,
    )

@router.get(
    "/spending/account/{account_id}/over-time",
    summary="Get spending for a single account over time",
    responses={
        200: {"description": "Monthly spending for the specified expense account"},
    },
)
async def get_single_account_spending_over_time(
    account_id: UUID,
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> TimeSeriesResponse:
    """
    Get monthly spending for a specific expense account.

    Enables drill-down from a dropdown selection:
    1. User selects "Groceries" from expense account dropdown
    2. Frontend fetches this endpoint with the Groceries account ID
    3. Line chart shows Groceries spending trend over time

    Returns time series data suitable for:
    - Line charts showing single category trend
    - Bar charts comparing months for one category
    - Identifying spending patterns in specific categories
    """
    query = SingleAccountSpendingQuery.from_factory(factory)
    result = await query.execute(
        account_id=account_id,
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TimeSeriesResponse(
        data_points=[
            TimeSeriesDataPointResponse(
                period=dp.period,
                period_label=dp.period_label,
                value=dp.value,
            )
            for dp in result.data_points
        ],
        currency=result.currency,
        total=result.total,
        average=result.average,
        min_value=result.min_value,
        max_value=result.max_value,
    )

@router.get(
    "/spending/breakdown",
    summary="Get spending breakdown by category",
    responses={
        200: {"description": "Spending distribution by expense category"},
    },
)
async def get_spending_breakdown(
    factory: RepoFactory,
    month: MonthParam = None,
    days: DaysParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> SpendingBreakdownResponse:
    """
    Get spending breakdown by expense category.

    Returns breakdown data suitable for:
    - Pie charts showing spending distribution
    - Donut charts with category breakdown
    - Bar charts comparing category spending

    If `days` is provided, it overrides `month`.
    If neither is provided, defaults to current month.

    Items are sorted by amount (highest first).
    """
    query = SpendingBreakdownQuery.from_factory(factory)
    result = await query.execute(
        month=month,
        days=days,
        include_drafts=include_drafts,
    )

    return SpendingBreakdownResponse(
        period_label=result.period_label,
        items=[
            BreakdownItemResponse(
                category=item.category,
                amount=item.amount,
                percentage=item.percentage,
                account_id=item.account_id,
            )
            for item in result.items
        ],
        total=result.total,
        currency=result.currency,
        category_count=result.category_count,
    )

@router.get(
    "/spending/top",
    summary="Get top expense categories",
    responses={
        200: {"description": "Ranked list of top expense categories"},
    },
)
async def get_top_expenses(
    factory: RepoFactory,
    months: MonthsParam = 3,
    top_n: TopNParam = 10,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> TopExpensesResponse:
    """
    Get top expense categories ranked by total spending.

    Returns ranked data suitable for:
    - Horizontal bar charts
    - Ranked lists showing where money goes
    - Identifying areas to cut spending

    Items include monthly average and percentage of total.
    """
    query = TopExpensesQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        top_n=top_n,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TopExpensesResponse(
        period_label=result.period_label,
        items=[
            TopExpenseItemResponse(
                rank=item.rank,
                category=item.category,
                account_id=item.account_id,
                total_amount=item.total_amount,
                monthly_average=item.monthly_average,
                percentage_of_total=item.percentage_of_total,
                transaction_count=item.transaction_count,
            )
            for item in result.items
        ],
        total_spending=result.total_spending,
        currency=result.currency,
        months_analyzed=result.months_analyzed,
    )

@router.get(
    "/income/over-time",
    summary="Get income over time",
    responses={
        200: {"description": "Monthly income totals"},
    },
)
async def get_income_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> TimeSeriesResponse:
    """
    Get monthly income totals.

    Returns time series data suitable for:
    - Line charts showing income trend
    - Salary growth visualization
    - Income comparison across months
    """
    query = IncomeOverTimeQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TimeSeriesResponse(
        data_points=[
            TimeSeriesDataPointResponse(
                period=dp.period,
                period_label=dp.period_label,
                value=dp.value,
            )
            for dp in result.data_points
        ],
        currency=result.currency,
        total=result.total,
        average=result.average,
        min_value=result.min_value,
        max_value=result.max_value,
    )

@router.get(
    "/income/breakdown",
    summary="Get income breakdown by source",
    responses={
        200: {"description": "Income distribution by source"},
    },
)
async def get_income_breakdown(
    factory: RepoFactory,
    month: MonthParam = None,
    days: DaysParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> IncomeBreakdownResponse:
    """
    Get income breakdown by source/account.

    Returns breakdown data suitable for:
    - Pie charts showing income composition
    - Understanding income diversification

    If `days` is provided, it overrides `month`.
    If neither is provided, defaults to current month.
    """
    query = IncomeBreakdownQuery.from_factory(factory)
    result = await query.execute(
        month=month,
        days=days,
        include_drafts=include_drafts,
    )

    return IncomeBreakdownResponse(
        period_label=result.period_label,
        items=[
            BreakdownItemResponse(
                category=item.category,
                amount=item.amount,
                percentage=item.percentage,
                account_id=item.account_id,
            )
            for item in result.items
        ],
        total=result.total,
        currency=result.currency,
    )

@router.get(
    "/net-income/over-time",
    summary="Get net income over time",
    responses={
        200: {"description": "Monthly net income (income - expenses)"},
    },
)
async def get_net_income_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> TimeSeriesResponse:
    """
    Get monthly net income (income minus expenses).

    Returns time series data suitable for:
    - Line charts showing savings trend
    - Bar charts with positive/negative values
    - Financial health visualization

    Positive values indicate savings, negative values indicate deficit.
    """
    query = NetIncomeOverTimeQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TimeSeriesResponse(
        data_points=[
            TimeSeriesDataPointResponse(
                period=dp.period,
                period_label=dp.period_label,
                value=dp.value,
            )
            for dp in result.data_points
        ],
        currency=result.currency,
        total=result.total,
        average=result.average,
        min_value=result.min_value,
        max_value=result.max_value,
    )

@router.get(
    "/savings-rate/over-time",
    summary="Get savings rate over time",
    responses={
        200: {"description": "Monthly savings rate percentage"},
    },
)
async def get_savings_rate_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> TimeSeriesResponse:
    """
    Get monthly savings rate (percentage of income saved).

    Formula: (income - expenses) / income * 100

    Returns time series data suitable for:
    - Line charts showing savings discipline
    - Goal tracking (e.g., target 20% savings rate)

    Negative values indicate spending exceeded income.
    Currency field will be "%" for this endpoint.
    """
    query = SavingsRateQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TimeSeriesResponse(
        data_points=[
            TimeSeriesDataPointResponse(
                period=dp.period,
                period_label=dp.period_label,
                value=dp.value,
            )
            for dp in result.data_points
        ],
        currency=result.currency,
        total=result.total,
        average=result.average,
        min_value=result.min_value,
        max_value=result.max_value,
    )

@router.get(
    "/net-worth/over-time",
    summary="Get net worth over time",
    responses={
        200: {"description": "Monthly net worth (assets - liabilities)"},
    },
)
async def get_net_worth_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = True,
) -> TimeSeriesResponse:
    """
    Get monthly net worth (total assets minus total liabilities).

    Returns time series data suitable for:
    - Line charts showing wealth building
    - Long-term financial health tracking

    The `total` field contains the latest (most recent) net worth value.
    """
    query = NetWorthQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return TimeSeriesResponse(
        data_points=[
            TimeSeriesDataPointResponse(
                period=dp.period,
                period_label=dp.period_label,
                value=dp.value,
            )
            for dp in result.data_points
        ],
        currency=result.currency,
        total=result.total,
        average=result.average,
        min_value=result.min_value,
        max_value=result.max_value,
    )

@router.get(
    "/balances/over-time",
    summary="Get account balances over time",
    responses={
        200: {"description": "Monthly balance history by account"},
    },
)
async def get_balances_over_time(
    factory: RepoFactory,
    months: MonthsParam = 12,
    end_month: EndMonthParam = None,
    include_drafts: IncludeDraftsParam = True,
) -> CategoryTimeSeriesResponse:
    """
    Get monthly balance history for asset accounts.

    Returns time series data suitable for:
    - Multi-line charts (one line per account)
    - Stacked area charts (total assets)
    - Savings growth visualization

    Accounts are sorted by latest balance (highest first).
    """
    query = BalanceHistoryQuery.from_factory(factory)
    result = await query.execute(
        months=months,
        end_month=end_month,
        include_drafts=include_drafts,
    )

    return CategoryTimeSeriesResponse(
        data_points=[
            CategoryDataResponse(
                period=dp.period,
                period_label=dp.period_label,
                categories=dp.categories,
                total=dp.total,
            )
            for dp in result.data_points
        ],
        categories=result.categories,
        currency=result.currency,
        totals_by_category=result.totals_by_category,
    )

@router.get(
    "/comparison/month-over-month",
    summary="Compare current vs previous month",
    responses={
        200: {"description": "Month-over-month comparison"},
    },
)
async def get_month_comparison(
    factory: RepoFactory,
    month: MonthParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> MonthComparisonResponse:
    """
    Compare financial metrics between current and previous month.

    Returns comparison data suitable for:
    - Dashboard summary cards with change indicators
    - Trend arrows (up/down)
    - Category-level change analysis

    If `month` is not provided, compares current month vs previous month.
    """
    query = MonthComparisonQuery.from_factory(factory)
    result = await query.execute(
        month=month,
        include_drafts=include_drafts,
    )

    return MonthComparisonResponse(
        current_month=result.current_month,
        previous_month=result.previous_month,
        currency=result.currency,
        current_income=result.current_income,
        previous_income=result.previous_income,
        income_change=result.income_change,
        income_change_percentage=result.income_change_percentage,
        current_spending=result.current_spending,
        previous_spending=result.previous_spending,
        spending_change=result.spending_change,
        spending_change_percentage=result.spending_change_percentage,
        current_net=result.current_net,
        previous_net=result.previous_net,
        net_change=result.net_change,
        net_change_percentage=result.net_change_percentage,
        category_comparisons=[
            CategoryComparisonResponse(
                category=cc.category,
                current_amount=cc.current_amount,
                previous_amount=cc.previous_amount,
                change_amount=cc.change_amount,
                change_percentage=cc.change_percentage,
            )
            for cc in result.category_comparisons
        ],
    )

@router.get(
    "/sankey",
    summary="Get Sankey diagram data for cash flow",
    responses={
        200: {"description": "Sankey nodes and links for cash flow visualization"},
    },
)
async def get_sankey_data(
    factory: RepoFactory,
    month: MonthParam = None,
    days: DaysParam = None,
    include_drafts: IncludeDraftsParam = False,
) -> SankeyResponse:
    """
    Get Sankey diagram data showing cash flow visualization.

    Returns nodes and links suitable for rendering a Sankey diagram
    that shows how money flows from income sources through to expense
    categories and savings.

    **Flow structure:**
    - Income sources → Total Income → Expense categories
    - If net income is positive, shows Savings as an outflow

    **Chart libraries:**
    - @nivo/sankey (React)
    - D3.js sankey
    - plotly.js

    If `days` is provided, it overrides `month`.
    If neither is provided, defaults to current month.
    """
    query = SankeyQuery.from_factory(factory)
    result = await query.execute(
        month=month,
        days=days,
        include_drafts=include_drafts,
    )

    return SankeyResponse(
        nodes=[
            SankeyNodeResponse(
                id=node.id,
                label=node.label,
                category=node.category,
                color=node.color,
            )
            for node in result.nodes
        ],
        links=[
            SankeyLinkResponse(
                source=link.source,
                target=link.target,
                value=link.value,
            )
            for link in result.links
        ],
        currency=result.currency,
        period_label=result.period_label,
        total_income=result.total_income,
        total_expenses=result.total_expenses,
        net_savings=result.net_savings,
    )
