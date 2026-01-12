"""Dashboard schemas for API request/response models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AccountBalanceResponse(BaseModel):
    """Response schema for account balance."""

    id: UUID = Field(..., description="Account unique identifier")
    name: str = Field(..., description="Account display name")
    balance: Decimal = Field(..., description="Current calculated balance")
    currency: str = Field(..., description="ISO 4217 currency code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "DKB Checking Account",
                "balance": "2543.67",
                "currency": "EUR",
            }
        }
    }


class CategorySpendingResponse(BaseModel):
    """Response schema for spending by category (expense account)."""

    category: str = Field(..., description="Expense account name (e.g., 'Groceries', 'Rent')")
    amount: Decimal = Field(..., description="Total spending amount in this category")
    currency: str = Field(default="EUR", description="ISO 4217 currency code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "Groceries",
                "amount": "345.67",
                "currency": "EUR",
            }
        }
    }


class RecentTransactionResponse(BaseModel):
    """Response schema for recent transaction in dashboard (simplified view)."""

    id: UUID = Field(..., description="Transaction unique identifier")
    date: datetime = Field(..., description="Transaction date")
    description: str = Field(..., description="Transaction description")
    amount: Decimal = Field(..., description="Transaction amount (always positive)")
    currency: str = Field(..., description="ISO 4217 currency code")
    is_income: bool = Field(..., description="Direction: True = income, False = expense")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "date": "2024-12-05T14:30:00Z",
                "description": "REWE Supermarket",
                "amount": "45.99",
                "currency": "EUR",
                "is_income": False,
            }
        }
    }


class DashboardSummaryResponse(BaseModel):
    """Comprehensive financial dashboard summary.

    Provides a complete overview of financial status including
    income/expenses, balances, spending breakdown, and recent activity.
    """

    period_label: str = Field(..., description="Human-readable period (e.g., 'December 2024', 'Last 30 days')")
    total_income: Decimal = Field(..., description="Total income for the period")
    total_expenses: Decimal = Field(..., description="Total expenses for the period")
    net_income: Decimal = Field(..., description="Net income (income - expenses)")
    account_balances: list[AccountBalanceResponse] = Field(
        ..., description="Current balances of all asset accounts"
    )
    category_spending: list[CategorySpendingResponse] = Field(
        ..., description="Spending breakdown by expense category (sorted by amount)"
    )
    recent_transactions: list[RecentTransactionResponse] = Field(
        ..., description="Most recent transactions (up to 10)"
    )
    draft_count: int = Field(..., description="Transactions pending review")
    posted_count: int = Field(..., description="Finalized transactions in period")

    model_config = {
        "json_schema_extra": {
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
                    {"category": "Transportation", "amount": "89.50", "currency": "EUR"},
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
            }
        }
    }


class SpendingBreakdownResponse(BaseModel):
    """Detailed spending breakdown by category."""

    period_label: str = Field(..., description="Human-readable period description")
    total_spending: Decimal = Field(..., description="Total spending across all categories")
    categories: list[CategorySpendingResponse] = Field(
        ..., description="Spending by expense category (sorted by amount, highest first)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "period_label": "December 2024",
                "total_spending": "1847.32",
                "categories": [
                    {"category": "Rent", "amount": "950.00", "currency": "EUR"},
                    {"category": "Groceries", "amount": "345.67", "currency": "EUR"},
                    {"category": "Utilities", "amount": "125.00", "currency": "EUR"},
                    {"category": "Transportation", "amount": "89.50", "currency": "EUR"},
                    {"category": "Entertainment", "amount": "67.15", "currency": "EUR"},
                ],
            }
        }
    }


class BalancesResponse(BaseModel):
    """Current balances for all asset accounts."""

    balances: list[AccountBalanceResponse] = Field(
        ..., description="Individual account balances"
    )
    total_assets: Decimal = Field(..., description="Sum of all asset account balances")

    model_config = {
        "json_schema_extra": {
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
            }
        }
    }

