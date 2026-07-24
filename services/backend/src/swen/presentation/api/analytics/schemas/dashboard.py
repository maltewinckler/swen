"""Dashboard schemas for API request/response models."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field

from swen.application.analytics.dtos import (
    AccountBalanceDTO,
    CategorySpendingDTO,
    DashboardSummaryDTO,
)


class DashboardSummaryResponse(DashboardSummaryDTO):
    """Comprehensive financial dashboard summary.

    Provides a complete overview of financial status including
    income/expenses, balances, spending breakdown, and recent activity.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "period_label": "December 2024",
                "total_income": "3500.00",
                "total_expenses": "1847.32",
                "net_income": "1652.68",
                "account_balances": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "DKB Checking Account",
                        "balance": "2543.67",
                        "currency": "EUR",
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Triodos Savings",
                        "balance": "5000.00",
                        "currency": "EUR",
                    },
                ],
                "category_spending": [
                    {"category": "Rent", "amount": "950.00", "currency": "EUR"},
                    {"category": "Groceries", "amount": "345.67", "currency": "EUR"},
                    {"category": "Utilities", "amount": "125.00", "currency": "EUR"},
                    {
                        "category": "Transportation",
                        "amount": "89.50",
                        "currency": "EUR",
                    },
                ],
                "recent_transactions": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "date": "2024-12-05T14:30:00Z",
                        "description": "REWE Supermarket",
                        "amount": "45.99",
                        "currency": "EUR",
                        "is_income": False,
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "date": "2024-12-01T09:00:00Z",
                        "description": "Salary December",
                        "amount": "3500.00",
                        "currency": "EUR",
                        "is_income": True,
                    },
                ],
                "draft_count": 3,
                "posted_count": 42,
            },
        },
    )


class SpendingBreakdownResponse(BaseModel):
    """Detailed spending breakdown by category."""

    period_label: str
    total_spending: Decimal
    categories: list[CategorySpendingDTO]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_label": "December 2024",
                "total_spending": "1847.32",
                "categories": [
                    {"category": "Rent", "amount": "950.00", "currency": "EUR"},
                    {"category": "Groceries", "amount": "345.67", "currency": "EUR"},
                    {"category": "Utilities", "amount": "125.00", "currency": "EUR"},
                    {
                        "category": "Transportation",
                        "amount": "89.50",
                        "currency": "EUR",
                    },
                    {"category": "Entertainment", "amount": "67.15", "currency": "EUR"},
                ],
            },
        },
    )


class BalancesResponse(BaseModel):
    """Current balances for all asset accounts."""

    balances: list[AccountBalanceDTO]

    @computed_field
    @property
    def total_assets(self) -> Decimal:
        """Calculate total assets from individual account balances."""
        return sum((b.balance for b in self.balances), Decimal(0))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "balances": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "DKB Checking Account",
                        "balance": "2543.67",
                        "currency": "EUR",
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "Triodos Savings",
                        "balance": "5000.00",
                        "currency": "EUR",
                    },
                ],
                "total_assets": "7543.67",
            },
        },
    )
