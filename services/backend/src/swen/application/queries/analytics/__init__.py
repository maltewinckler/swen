"""Analytics queries for financial visualization and reporting."""

from swen.application.dtos.analytics import (
    CategoryComparison,
    MonthComparisonResult,
    SankeyData,
    SankeyLink,
    SankeyNode,
    TopExpenseItem,
    TopExpensesResult,
)
from swen.application.queries.analytics.balance_history_query import (
    BalanceHistoryQuery,
)
from swen.application.queries.analytics.income_breakdown_query import (
    IncomeBreakdownQuery,
)
from swen.application.queries.analytics.income_over_time_query import (
    IncomeOverTimeQuery,
)
from swen.application.queries.analytics.month_comparison_query import (
    MonthComparisonQuery,
)
from swen.application.queries.analytics.net_income_over_time_query import (
    NetIncomeOverTimeQuery,
)
from swen.application.queries.analytics.net_worth_query import (
    NetWorthQuery,
)
from swen.application.queries.analytics.sankey_query import (
    SankeyQuery,
)
from swen.application.queries.analytics.savings_rate_query import (
    SavingsRateQuery,
)
from swen.application.queries.analytics.single_account_spending_query import (
    SingleAccountSpendingQuery,
)
from swen.application.queries.analytics.spending_breakdown_query import (
    SpendingBreakdownQuery,
)
from swen.application.queries.analytics.spending_over_time_query import (
    SpendingOverTimeQuery,
)
from swen.application.queries.analytics.top_expenses_query import (
    TopExpensesQuery,
)

__all__ = [
    "BalanceHistoryQuery",
    "CategoryComparison",
    "IncomeBreakdownQuery",
    "IncomeOverTimeQuery",
    "MonthComparisonQuery",
    "MonthComparisonResult",
    "NetIncomeOverTimeQuery",
    "NetWorthQuery",
    "SankeyData",
    "SankeyLink",
    "SankeyNode",
    "SankeyQuery",
    "SavingsRateQuery",
    "SingleAccountSpendingQuery",
    "SpendingBreakdownQuery",
    "SpendingOverTimeQuery",
    "TopExpenseItem",
    "TopExpensesQuery",
    "TopExpensesResult",
]
