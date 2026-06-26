"""Analytics DTOs for visualization and reporting.

These DTOs provide data structures optimized for frontend chart rendering,
including time series data for line/bar charts and breakdowns for pie charts.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series (e.g., monthly totals)."""

    model_config = ConfigDict(frozen=True)

    period: str
    period_label: str
    value: Decimal


class CategoryTimeSeriesDataPoint(BaseModel):
    """Data point with category breakdown for a single period."""

    model_config = ConfigDict(frozen=True)

    period: str
    period_label: str
    categories: dict[str, Decimal]
    total: Decimal


class TimeSeriesResult(BaseModel):
    """Result for simple time series queries.

    Used for:
    - Total income over time
    - Net income over time
    - Single account balance over time
    """

    model_config = ConfigDict(frozen=True)

    data_points: list[TimeSeriesDataPoint]
    currency: str
    total: Decimal  # Sum of all values
    average: Decimal  # Average per period
    min_value: Decimal = Decimal("0")
    max_value: Decimal = Decimal("0")


class CategoryTimeSeriesResult(BaseModel):
    """Result for time series with category breakdown.

    Used for:
    - Spending by category over time (stacked bar chart)
    - Income by source over time (multi-line chart)
    - Account balances over time (multi-line chart)
    """

    model_config = ConfigDict(frozen=True)

    data_points: list[CategoryTimeSeriesDataPoint]
    categories: list[str]
    currency: str
    totals_by_category: dict[str, Decimal] = {}


class BreakdownItem(BaseModel):
    """Single category in a breakdown (for pie charts).

    Represents one slice of a pie chart with its value,
    percentage of total, and associated account ID for drill-down.
    """

    model_config = ConfigDict(frozen=True)

    category: str  # Account name (e.g., "Groceries")
    amount: Decimal
    percentage: Decimal  # 0-100 scale
    account_id: str  # For drill-down navigation


class SpendingBreakdownResult(BaseModel):
    """Result for spending breakdown (pie chart data).

    Shows how spending is distributed across expense categories
    for a given period.
    """

    model_config = ConfigDict(frozen=True)

    period_label: str  # "December 2024" or "Last 30 days"
    items: list[BreakdownItem] = []
    total: Decimal
    currency: str
    category_count: int = 0  # Number of categories with spending

    @computed_field
    @property
    def category_count_display(self) -> int:
        return self.category_count


class IncomeBreakdownResult(BaseModel):
    """Result for income breakdown (pie chart data).

    Shows how income is distributed across income sources.
    """

    model_config = ConfigDict(frozen=True)

    period_label: str
    items: list[BreakdownItem] = []
    total: Decimal
    currency: str


class CategoryComparison(BaseModel):
    """Comparison data for a single category (month-over-month)."""

    model_config = ConfigDict(frozen=True)

    category: str
    current_amount: Decimal
    previous_amount: Decimal
    change_amount: Decimal
    change_percentage: Decimal  # Can be negative


class MonthComparisonResult(BaseModel):
    """Result of month-over-month comparison."""

    model_config = ConfigDict(frozen=True)

    current_month: str
    previous_month: str
    currency: str

    # Income comparison
    current_income: Decimal
    previous_income: Decimal
    income_change: Decimal
    income_change_percentage: Decimal

    # Spending comparison
    current_spending: Decimal
    previous_spending: Decimal
    spending_change: Decimal
    spending_change_percentage: Decimal

    # Net income comparison
    current_net: Decimal
    previous_net: Decimal
    net_change: Decimal
    net_change_percentage: Decimal

    # Category-level breakdown (spending)
    category_comparisons: list[CategoryComparison] = []


class TopExpenseItem(BaseModel):
    """A single top expense category."""

    model_config = ConfigDict(frozen=True)

    rank: int
    category: str
    account_id: str
    total_amount: Decimal
    monthly_average: Decimal
    percentage_of_total: Decimal
    transaction_count: int


class TopExpensesResult(BaseModel):
    """Result of top expenses query."""

    model_config = ConfigDict(frozen=True)

    period_label: str
    items: list[TopExpenseItem] = []
    total_spending: Decimal
    currency: str
    months_analyzed: int
