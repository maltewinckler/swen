"""Analytics queries for financial visualization and reporting."""

from swen.application.analytics.dtos import (
    CategoryComparisonDTO,
    MonthComparisonResultDTO,
    SankeyDataDTO,
    SankeyLinkDTO,
    SankeyNodeDTO,
    TopExpenseItemDTO,
    TopExpensesResultDTO,
)
from swen.application.analytics.queries.balance_history_query import (
    BalanceHistoryQuery,
)
from swen.application.analytics.queries.dashboard_summary_query import (
    DashboardSummaryQuery,
)
from swen.application.analytics.queries.export_data_query import ExportDataQuery
from swen.application.analytics.queries.export_report_query import ExportReportQuery
from swen.application.analytics.queries.income_breakdown_query import (
    IncomeBreakdownQuery,
)
from swen.application.analytics.queries.income_over_time_query import (
    IncomeOverTimeQuery,
)
from swen.application.analytics.queries.month_comparison_query import (
    MonthComparisonQuery,
)
from swen.application.analytics.queries.net_income_over_time_query import (
    NetIncomeOverTimeQuery,
)
from swen.application.analytics.queries.net_worth_query import (
    NetWorthQuery,
)
from swen.application.analytics.queries.sankey_query import (
    SankeyQuery,
)
from swen.application.analytics.queries.savings_rate_query import (
    SavingsRateQuery,
)
from swen.application.analytics.queries.single_account_spending_query import (
    SingleAccountSpendingQuery,
)
from swen.application.analytics.queries.spending_breakdown_query import (
    SpendingBreakdownQuery,
)
from swen.application.analytics.queries.spending_over_time_query import (
    SpendingOverTimeQuery,
)
from swen.application.analytics.queries.top_expenses_query import (
    TopExpensesQuery,
)

__all__ = [
    "BalanceHistoryQuery",
    "CategoryComparisonDTO",
    "IncomeBreakdownQuery",
    "IncomeOverTimeQuery",
    "MonthComparisonQuery",
    "MonthComparisonResultDTO",
    "NetIncomeOverTimeQuery",
    "NetWorthQuery",
    "SankeyDataDTO",
    "SankeyLinkDTO",
    "SankeyNodeDTO",
    "SankeyQuery",
    "SavingsRateQuery",
    "SingleAccountSpendingQuery",
    "SpendingBreakdownQuery",
    "SpendingOverTimeQuery",
    "TopExpenseItemDTO",
    "TopExpensesQuery",
    "TopExpensesResultDTO",
    "DashboardSummaryQuery",
    "ExportDataQuery",
    "ExportReportQuery",
]
