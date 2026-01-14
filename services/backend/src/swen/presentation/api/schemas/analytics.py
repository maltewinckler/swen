"""Pydantic schemas for analytics endpoints.

These schemas define the API response structure for chart data,
optimized for frontend visualization libraries.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class TimeSeriesDataPointResponse(BaseModel):
    """Single data point in a time series.

    Use `period` for programmatic access (sorting, filtering).
    Use `period_label` for display in chart axes.
    """

    period: str = Field(description="Period identifier in YYYY-MM format (sortable)")
    period_label: str = Field(description="Human-readable label (e.g., 'Dec 2024')")
    value: Decimal = Field(description="Numeric value for this period")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": "2024-12",
                "period_label": "Dec 2024",
                "value": "3245.67",
            }
        }
    )

class CategoryDataResponse(BaseModel):
    """Category breakdown for a single period.

    Used for stacked bar charts and multi-line charts where
    each category is a separate series.
    """

    period: str = Field(description="Period identifier in YYYY-MM format")
    period_label: str = Field(description="Human-readable label for chart axis")
    categories: dict[str, Decimal] = Field(description="Amount per category (category name → amount)")
    total: Decimal = Field(description="Sum of all categories for this period")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": "2024-12",
                "period_label": "Dec 2024",
                "categories": {
                    "Groceries": "345.67",
                    "Rent": "950.00",
                    "Utilities": "125.00",
                    "Transportation": "89.50",
                },
                "total": "1510.17",
            }
        }
    )

class TimeSeriesResponse(BaseModel):
    """Response for simple time series data.

    Ideal for line charts showing trends over time.
    Includes summary statistics for dashboard cards.

    **Chart types:**
    - Line chart (income/expense trends)
    - Bar chart (monthly comparisons)
    - Area chart (cumulative view)
    """

    data_points: list[TimeSeriesDataPointResponse] = Field(
        description="Chronologically ordered data points"
    )
    currency: str = Field(description="Unit: 'EUR', 'USD' or '%' for rates")
    total: Decimal = Field(description="Sum of all values (or latest for net worth)")
    average: Decimal = Field(description="Average value per period")
    min_value: Decimal = Field(description="Lowest value in series (for chart scaling)")
    max_value: Decimal = Field(description="Highest value in series (for chart scaling)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_points": [
                    {"period": "2024-10", "period_label": "Oct 2024", "value": "3200.00"},
                    {"period": "2024-11", "period_label": "Nov 2024", "value": "3350.00"},
                    {"period": "2024-12", "period_label": "Dec 2024", "value": "3500.00"},
                ],
                "currency": "EUR",
                "total": "10050.00",
                "average": "3350.00",
                "min_value": "3200.00",
                "max_value": "3500.00",
            }
        }
    )

class CategoryTimeSeriesResponse(BaseModel):
    """Response for time series with category breakdown.

    Ideal for multi-series visualizations where you want to see
    how different categories change over time.

    **Chart types:**
    - Stacked bar chart (spending by category per month)
    - Multi-line chart (one line per category)
    - Stacked area chart (cumulative categories)
    """

    data_points: list[CategoryDataResponse] = Field(
        description="Chronologically ordered data with category breakdown"
    )
    categories: list[str] = Field(
        description="Category names for chart legend (sorted by total, highest first)"
    )
    currency: str = Field(description="Currency code (e.g., 'EUR')")
    totals_by_category: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Grand total per category (for sorting legend by importance)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_points": [
                    {
                        "period": "2024-11",
                        "period_label": "Nov 2024",
                        "categories": {"Rent": "950.00", "Groceries": "320.00", "Utilities": "110.00"},
                        "total": "1380.00",
                    },
                    {
                        "period": "2024-12",
                        "period_label": "Dec 2024",
                        "categories": {"Rent": "950.00", "Groceries": "345.67", "Utilities": "125.00"},
                        "total": "1420.67",
                    },
                ],
                "categories": ["Rent", "Groceries", "Utilities"],
                "currency": "EUR",
                "totals_by_category": {
                    "Rent": "1900.00",
                    "Groceries": "665.67",
                    "Utilities": "235.00",
                },
            }
        }
    )

class BreakdownItemResponse(BaseModel):
    """Single item in a breakdown (pie chart slice).

    Each item represents one slice of a pie/donut chart.
    Use `percentage` for proportional sizing.
    Use `account_id` to link to transaction drill-down.
    """

    category: str = Field(description="Category display name (for labels)")
    amount: Decimal = Field(description="Absolute amount in this category")
    percentage: Decimal = Field(description="Percentage of total (0-100)")
    account_id: str = Field(description="Account UUID for filtering transactions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "Groceries",
                "amount": "345.67",
                "percentage": "23.4",
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )

class SpendingBreakdownResponse(BaseModel):
    """Spending distribution by expense category.

    **Chart types:**
    - Pie chart (proportional spending)
    - Donut chart (with total in center)
    - Horizontal bar chart (ranked categories)
    """

    period_label: str = Field(description="Human-readable period (e.g., 'December 2024')")
    items: list[BreakdownItemResponse] = Field(
        description="Expense categories sorted by amount (highest first)"
    )
    total: Decimal = Field(description="Total spending across all categories")
    currency: str = Field(description="Currency code (e.g., 'EUR')")
    category_count: int = Field(description="Number of expense categories with activity")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_label": "December 2024",
                "items": [
                    {
                        "category": "Rent",
                        "amount": "950.00",
                        "percentage": "51.4",
                        "account_id": "660e8400-e29b-41d4-a716-446655440001",
                    },
                    {
                        "category": "Groceries",
                        "amount": "345.67",
                        "percentage": "18.7",
                        "account_id": "660e8400-e29b-41d4-a716-446655440002",
                    },
                    {
                        "category": "Utilities",
                        "amount": "125.00",
                        "percentage": "6.8",
                        "account_id": "660e8400-e29b-41d4-a716-446655440003",
                    },
                ],
                "total": "1847.32",
                "currency": "EUR",
                "category_count": 8,
            }
        }
    )

class IncomeBreakdownResponse(BaseModel):
    """Income distribution by source.

    Shows where your money comes from (salary, interest, etc.).

    **Chart types:**
    - Pie chart (income composition)
    - Donut chart (total income in center)
    """

    period_label: str = Field(description="Human-readable period")
    items: list[BreakdownItemResponse] = Field(
        description="Income sources sorted by amount (highest first)"
    )
    total: Decimal = Field(description="Total income from all sources")
    currency: str = Field(description="Currency code (e.g., 'EUR')")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_label": "December 2024",
                "items": [
                    {
                        "category": "Salary",
                        "amount": "3500.00",
                        "percentage": "95.9",
                        "account_id": "770e8400-e29b-41d4-a716-446655440001",
                    },
                    {
                        "category": "Interest",
                        "amount": "12.50",
                        "percentage": "0.3",
                        "account_id": "770e8400-e29b-41d4-a716-446655440002",
                    },
                    {
                        "category": "Dividends",
                        "amount": "137.50",
                        "percentage": "3.8",
                        "account_id": "770e8400-e29b-41d4-a716-446655440003",
                    },
                ],
                "total": "3650.00",
                "currency": "EUR",
            }
        }
    )

class CategoryComparisonResponse(BaseModel):
    """Month-over-month comparison for a single category.

    Positive `change_percentage` = increased spending (usually bad).
    Negative `change_percentage` = decreased spending (usually good).
    """

    category: str = Field(description="Expense category name")
    current_amount: Decimal = Field(description="Spending in current month")
    previous_amount: Decimal = Field(description="Spending in previous month")
    change_amount: Decimal = Field(description="Absolute change (current - previous)")
    change_percentage: Decimal = Field(description="Percentage change (positive = increase)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "Groceries",
                "current_amount": "345.67",
                "previous_amount": "320.00",
                "change_amount": "25.67",
                "change_percentage": "8.02",
            }
        }
    )

class MonthComparisonResponse(BaseModel):
    """Month-over-month financial comparison.

    Perfect for dashboard summary cards with trend indicators.
    Use `change_percentage` to show ↑ or ↓ arrows.

    **Display tips:**
    - Income: positive change = good (green ↑)
    - Spending: positive change = bad (red ↑)
    - Net income: positive change = good (green ↑)
    """

    current_month: str = Field(description="Current month label (e.g., 'December 2024')")
    previous_month: str = Field(description="Previous month label (e.g., 'November 2024')")
    currency: str = Field(description="Currency code (e.g., 'EUR')")

    # Income comparison
    current_income: Decimal = Field(description="Total income this month")
    previous_income: Decimal = Field(description="Total income last month")
    income_change: Decimal = Field(description="Income difference (current - previous)")
    income_change_percentage: Decimal = Field(description="Income change percentage")

    # Spending comparison
    current_spending: Decimal = Field(description="Total spending this month")
    previous_spending: Decimal = Field(description="Total spending last month")
    spending_change: Decimal = Field(description="Spending difference")
    spending_change_percentage: Decimal = Field(description="Spending change percentage")

    # Net income comparison
    current_net: Decimal = Field(description="Net income this month (income - spending)")
    previous_net: Decimal = Field(description="Net income last month")
    net_change: Decimal = Field(description="Net income difference")
    net_change_percentage: Decimal = Field(description="Net income change percentage")

    # Category breakdown
    category_comparisons: list[CategoryComparisonResponse] = Field(
        default_factory=list,
        description="Per-category spending changes",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_month": "December 2024",
                "previous_month": "November 2024",
                "currency": "EUR",
                "current_income": "3500.00",
                "previous_income": "3350.00",
                "income_change": "150.00",
                "income_change_percentage": "4.48",
                "current_spending": "1847.32",
                "previous_spending": "1623.45",
                "spending_change": "223.87",
                "spending_change_percentage": "13.79",
                "current_net": "1652.68",
                "previous_net": "1726.55",
                "net_change": "-73.87",
                "net_change_percentage": "-4.28",
                "category_comparisons": [
                    {
                        "category": "Groceries",
                        "current_amount": "345.67",
                        "previous_amount": "320.00",
                        "change_amount": "25.67",
                        "change_percentage": "8.02",
                    },
                    {
                        "category": "Entertainment",
                        "current_amount": "150.00",
                        "previous_amount": "85.00",
                        "change_amount": "65.00",
                        "change_percentage": "76.47",
                    },
                ],
            }
        }
    )

class TopExpenseItemResponse(BaseModel):
    """A ranked expense category with statistics.

    Useful for identifying spending patterns and areas to optimize.
    """

    rank: int = Field(description="Position in ranking (1 = highest spending)")
    category: str = Field(description="Expense category name")
    account_id: str = Field(description="Account UUID for transaction drill-down")
    total_amount: Decimal = Field(description="Total spent in analysis period")
    monthly_average: Decimal = Field(description="Average monthly spending")
    percentage_of_total: Decimal = Field(description="Share of total spending (0-100)")
    transaction_count: int = Field(description="Number of transactions in this category")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rank": 1,
                "category": "Rent",
                "account_id": "660e8400-e29b-41d4-a716-446655440001",
                "total_amount": "2850.00",
                "monthly_average": "950.00",
                "percentage_of_total": "51.4",
                "transaction_count": 3,
            }
        }
    )

class TopExpensesResponse(BaseModel):
    """Ranked list of top expense categories.

    **Chart types:**
    - Horizontal bar chart (ranked spending)
    - Leaderboard list with progress bars

    **Use cases:**
    - Identify biggest spending areas
    - Find opportunities to reduce expenses
    - Track category trends over time
    """

    period_label: str = Field(description="Analysis period (e.g., 'Last 3 months')")
    items: list[TopExpenseItemResponse] = Field(
        description="Expense categories ranked by total amount"
    )
    total_spending: Decimal = Field(description="Sum of all spending in period")
    currency: str = Field(description="Currency code (e.g., 'EUR')")
    months_analyzed: int = Field(description="Number of months included in analysis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_label": "October - December 2024",
                "items": [
                    {
                        "rank": 1,
                        "category": "Rent",
                        "account_id": "660e8400-e29b-41d4-a716-446655440001",
                        "total_amount": "2850.00",
                        "monthly_average": "950.00",
                        "percentage_of_total": "51.4",
                        "transaction_count": 3,
                    },
                    {
                        "rank": 2,
                        "category": "Groceries",
                        "account_id": "660e8400-e29b-41d4-a716-446655440002",
                        "total_amount": "987.32",
                        "monthly_average": "329.11",
                        "percentage_of_total": "17.8",
                        "transaction_count": 24,
                    },
                    {
                        "rank": 3,
                        "category": "Utilities",
                        "account_id": "660e8400-e29b-41d4-a716-446655440003",
                        "total_amount": "360.00",
                        "monthly_average": "120.00",
                        "percentage_of_total": "6.5",
                        "transaction_count": 6,
                    },
                ],
                "total_spending": "5543.96",
                "currency": "EUR",
                "months_analyzed": 3,
            }
        }
    )

class SankeyNodeResponse(BaseModel):
    """A node in the Sankey diagram.

    Represents an income source, expense category, or the central total node.
    """

    id: str = Field(description="Unique node identifier (e.g., 'income_salary')")
    label: str = Field(description="Display label (e.g., 'Salary')")
    category: str = Field(description="Node type: 'income', 'total', 'expense', or 'savings'")
    color: str | None = Field(default=None, description="Hex color for the node")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "income_salary",
                "label": "Salary",
                "category": "income",
                "color": "#22c55e",
            }
        }
    )

class SankeyLinkResponse(BaseModel):
    """A link (flow) between two Sankey nodes.

    The width is proportional to the value, showing money flow magnitude.
    """

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    value: Decimal = Field(description="Flow amount (always positive)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "income_salary",
                "target": "total",
                "value": "3500.00",
            }
        }
    )

class SankeyResponse(BaseModel):
    """Sankey diagram data for cash flow visualization.

    Shows how money flows from income sources through expenses to savings.

    **Flow structure:**
    ```
    Income Sources → Total Income → Expense Categories
                                  → Savings (if positive)
    ```

    **Chart libraries:**
    - @nivo/sankey (React)
    - D3.js sankey
    - plotly.js
    """

    nodes: list[SankeyNodeResponse] = Field(description="All nodes in the diagram")
    links: list[SankeyLinkResponse] = Field(description="Links connecting nodes")
    currency: str = Field(description="Currency code (e.g., 'EUR')")
    period_label: str = Field(description="Human-readable period (e.g., 'December 2024')")
    total_income: Decimal = Field(description="Sum of all income")
    total_expenses: Decimal = Field(description="Sum of all expenses")
    net_savings: Decimal = Field(description="Income minus expenses (can be negative)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nodes": [
                    {"id": "income_salary", "label": "Salary", "category": "income", "color": "#22c55e"},
                    {"id": "income_dividends", "label": "Dividends", "category": "income", "color": "#16a34a"},
                    {"id": "total", "label": "Total Income", "category": "total", "color": "#6b7280"},
                    {"id": "expense_rent", "label": "Rent", "category": "expense", "color": "#f97316"},
                    {"id": "expense_food", "label": "Food", "category": "expense", "color": "#ef4444"},
                    {"id": "savings", "label": "Savings", "category": "savings", "color": "#22c55e"},
                ],
                "links": [
                    {"source": "income_salary", "target": "total", "value": "3500.00"},
                    {"source": "income_dividends", "target": "total", "value": "150.00"},
                    {"source": "total", "target": "expense_rent", "value": "950.00"},
                    {"source": "total", "target": "expense_food", "value": "450.00"},
                    {"source": "total", "target": "savings", "value": "2250.00"},
                ],
                "currency": "EUR",
                "period_label": "December 2024",
                "total_income": "3650.00",
                "total_expenses": "1400.00",
                "net_savings": "2250.00",
            }
        }
    )
