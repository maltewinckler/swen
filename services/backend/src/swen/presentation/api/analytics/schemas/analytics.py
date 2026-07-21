"""Pydantic schemas for analytics endpoints.

These schemas define the API response structure for chart data,
optimized for frontend visualization libraries.
"""

from pydantic import ConfigDict

from swen.application.analytics.dtos import (
    CategoryTimeSeriesResultDTO,
    IncomeBreakdownResultDTO,
    MonthComparisonResultDTO,
    SankeyDataDTO,
    SpendingBreakdownResultDTO,
    TimeSeriesResultDTO,
    TopExpensesResultDTO,
)


class TimeSeriesResponse(TimeSeriesResultDTO):
    """Response for simple time series data.

    Ideal for line charts showing trends over time.
    Includes summary statistics for dashboard cards.

    **Chart types:**
    - Line chart (income/expense trends)
    - Bar chart (monthly comparisons)
    - Area chart (cumulative view)
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "data_points": [
                    {
                        "period": "2024-10",
                        "period_label": "Oct 2024",
                        "value": "3200.00",
                    },
                    {
                        "period": "2024-11",
                        "period_label": "Nov 2024",
                        "value": "3350.00",
                    },
                    {
                        "period": "2024-12",
                        "period_label": "Dec 2024",
                        "value": "3500.00",
                    },
                ],
                "currency": "EUR",
                "total": "10050.00",
                "average": "3350.00",
                "min_value": "3200.00",
                "max_value": "3500.00",
            }
        },
    )


class CategoryTimeSeriesResponse(CategoryTimeSeriesResultDTO):
    """Response for time series with category breakdown.

    Ideal for multi-series visualizations where you want to see
    how different categories change over time.

    **Chart types:**
    - Stacked bar chart (spending by category per month)
    - Multi-line chart (one line per category)
    - Stacked area chart (cumulative categories)
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "data_points": [
                    {
                        "period": "2024-11",
                        "period_label": "Nov 2024",
                        "categories": {
                            "Rent": "950.00",
                            "Groceries": "320.00",
                            "Utilities": "110.00",
                        },
                        "total": "1380.00",
                    },
                    {
                        "period": "2024-12",
                        "period_label": "Dec 2024",
                        "categories": {
                            "Rent": "950.00",
                            "Groceries": "345.67",
                            "Utilities": "125.00",
                        },
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
        },
    )


class SpendingBreakdownResponse(SpendingBreakdownResultDTO):
    """Spending distribution by expense category.

    **Chart types:**
    - Pie chart (proportional spending)
    - Donut chart (with total in center)
    - Horizontal bar chart (ranked categories)
    """

    model_config = ConfigDict(
        from_attributes=True,
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
        },
    )


class IncomeBreakdownResponse(IncomeBreakdownResultDTO):
    """Income distribution by source.

    Shows where your money comes from (salary, interest, etc.).

    **Chart types:**
    - Pie chart (income composition)
    - Donut chart (total income in center)
    """

    model_config = ConfigDict(
        from_attributes=True,
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
        },
    )


class MonthComparisonResponse(MonthComparisonResultDTO):
    """Month-over-month financial comparison.

    Perfect for dashboard summary cards with trend indicators.
    Use `change_percentage` to show ↑ or ↓ arrows.

    **Display tips:**
    - Income: positive change = good (green ↑)
    - Spending: positive change = bad (red ↑)
    - Net income: positive change = good (green ↑)
    """

    model_config = ConfigDict(
        from_attributes=True,
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
        },
    )


class TopExpensesResponse(TopExpensesResultDTO):
    """Ranked list of top expense categories.

    **Chart types:**
    - Horizontal bar chart (ranked spending)
    - Leaderboard list with progress bars

    **Use cases:**
    - Identify biggest spending areas
    - Find opportunities to reduce expenses
    - Track category trends over time
    """

    model_config = ConfigDict(
        from_attributes=True,
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
        },
    )


class SankeyResponse(SankeyDataDTO):
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "nodes": [
                    {
                        "id": "income_salary",
                        "label": "Salary",
                        "category": "income",
                        "color": "#22c55e",
                    },
                    {
                        "id": "income_dividends",
                        "label": "Dividends",
                        "category": "income",
                        "color": "#16a34a",
                    },
                    {
                        "id": "total",
                        "label": "Total Income",
                        "category": "total",
                        "color": "#6b7280",
                    },
                    {
                        "id": "expense_rent",
                        "label": "Rent",
                        "category": "expense",
                        "color": "#f97316",
                    },
                    {
                        "id": "expense_food",
                        "label": "Food",
                        "category": "expense",
                        "color": "#ef4444",
                    },
                    {
                        "id": "savings",
                        "label": "Savings",
                        "category": "savings",
                        "color": "#22c55e",
                    },
                ],
                "links": [
                    {"source": "income_salary", "target": "total", "value": "3500.00"},
                    {
                        "source": "income_dividends",
                        "target": "total",
                        "value": "150.00",
                    },
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
        },
    )
