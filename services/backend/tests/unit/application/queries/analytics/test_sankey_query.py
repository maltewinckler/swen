"""Unit tests for SankeyQuery."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import (
    BreakdownItem,
    IncomeBreakdownResult,
    SankeyData,
    SpendingBreakdownResult,
)
from swen.application.queries.analytics import SankeyQuery


class TestSankeyQuery:
    """Test cases for SankeyQuery execution."""

    @pytest.mark.asyncio
    async def test_execute_returns_sankey_data_with_income_expenses_and_savings(self):
        """Test that query returns properly structured Sankey data."""
        port = AsyncMock()

        # Mock income breakdown
        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Salary",
                    amount=Decimal("3500"),
                    percentage=Decimal("87.5"),
                    account_id="income-1",
                ),
                BreakdownItem(
                    category="Dividends",
                    amount=Decimal("500"),
                    percentage=Decimal("12.5"),
                    account_id="income-2",
                ),
            ],
            total=Decimal("4000"),
            currency="EUR",
        )

        # Mock spending breakdown
        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Rent",
                    amount=Decimal("1200"),
                    percentage=Decimal("60"),
                    account_id="expense-1",
                ),
                BreakdownItem(
                    category="Food",
                    amount=Decimal("600"),
                    percentage=Decimal("30"),
                    account_id="expense-2",
                ),
                BreakdownItem(
                    category="Transport",
                    amount=Decimal("200"),
                    percentage=Decimal("10"),
                    account_id="expense-3",
                ),
            ],
            total=Decimal("2000"),
            currency="EUR",
            category_count=3,
        )

        query = SankeyQuery(port)
        result = await query.execute(month="2024-12", include_drafts=True)

        # Verify structure
        assert isinstance(result, SankeyData)
        assert result.currency == "EUR"
        assert result.period_label == "December 2024"
        assert result.total_income == Decimal("4000")
        assert result.total_expenses == Decimal("2000")
        assert result.net_savings == Decimal("2000")

        # Verify nodes: 2 income + 1 total + 3 expense + 1 savings = 7
        assert len(result.nodes) == 7

        # Check node categories
        income_nodes = [n for n in result.nodes if n.category == "income"]
        total_nodes = [n for n in result.nodes if n.category == "total"]
        expense_nodes = [n for n in result.nodes if n.category == "expense"]
        savings_nodes = [n for n in result.nodes if n.category == "savings"]

        assert len(income_nodes) == 2
        assert len(total_nodes) == 1
        assert len(expense_nodes) == 3
        assert len(savings_nodes) == 1

        # Verify links: 2 income→total + 3 total→expense + 1 total→savings = 6
        assert len(result.links) == 6

        # Check income links go to total
        income_links = [l for l in result.links if l.target == "total"]
        assert len(income_links) == 2
        assert sum(l.value for l in income_links) == Decimal("4000")

        # Check expense links come from total
        expense_links = [
            l
            for l in result.links
            if l.source == "total" and l.target.startswith("expense")
        ]
        assert len(expense_links) == 3
        assert sum(l.value for l in expense_links) == Decimal("2000")

        # Check savings link
        savings_links = [l for l in result.links if l.target == "savings"]
        assert len(savings_links) == 1
        assert savings_links[0].value == Decimal("2000")

    @pytest.mark.asyncio
    async def test_execute_no_savings_when_expenses_exceed_income(self):
        """Test that no savings node is created when expenses >= income."""
        port = AsyncMock()

        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Salary",
                    amount=Decimal("2000"),
                    percentage=Decimal("100"),
                    account_id="income-1",
                ),
            ],
            total=Decimal("2000"),
            currency="EUR",
        )

        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Rent",
                    amount=Decimal("1500"),
                    percentage=Decimal("60"),
                    account_id="expense-1",
                ),
                BreakdownItem(
                    category="Food",
                    amount=Decimal("700"),
                    percentage=Decimal("28"),
                    account_id="expense-2",
                ),
                BreakdownItem(
                    category="Entertainment",
                    amount=Decimal("300"),
                    percentage=Decimal("12"),
                    account_id="expense-3",
                ),
            ],
            total=Decimal("2500"),
            currency="EUR",
            category_count=3,
        )

        query = SankeyQuery(port)
        result = await query.execute(month="2024-12")

        # Net savings is negative
        assert result.net_savings == Decimal("-500")

        # No savings node when expenses exceed income
        savings_nodes = [n for n in result.nodes if n.category == "savings"]
        assert len(savings_nodes) == 0

        # No savings link
        savings_links = [l for l in result.links if l.target == "savings"]
        assert len(savings_links) == 0

    @pytest.mark.asyncio
    async def test_execute_empty_data_returns_minimal_structure(self):
        """Test that empty data returns at least the total node."""
        port = AsyncMock()

        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="December 2024",
            items=[],
            total=Decimal("0"),
            currency="EUR",
        )

        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="December 2024",
            items=[],
            total=Decimal("0"),
            currency="EUR",
            category_count=0,
        )

        query = SankeyQuery(port)
        result = await query.execute(month="2024-12")

        # Should have only the total node
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "total"
        assert result.nodes[0].category == "total"

        # No links with no income/expenses
        assert len(result.links) == 0

        # Zero values
        assert result.total_income == Decimal("0")
        assert result.total_expenses == Decimal("0")
        assert result.net_savings == Decimal("0")

    @pytest.mark.asyncio
    async def test_execute_passes_params_to_analytics_port(self):
        """Test that query parameters are passed correctly to the analytics port."""
        port = AsyncMock()

        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="Last 30 days",
            items=[],
            total=Decimal("0"),
            currency="EUR",
        )
        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="Last 30 days",
            items=[],
            total=Decimal("0"),
            currency="EUR",
            category_count=0,
        )

        query = SankeyQuery(port)
        await query.execute(month="2024-12", days=30, include_drafts=True)

        # Verify both methods were called with correct params
        port.income_breakdown.assert_awaited_once_with(
            month="2024-12",
            days=30,
            include_drafts=True,
        )
        port.spending_breakdown.assert_awaited_once_with(
            month="2024-12",
            days=30,
            include_drafts=True,
        )

    @pytest.mark.asyncio
    async def test_nodes_have_colors(self):
        """Test that all nodes have colors assigned."""
        port = AsyncMock()

        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Salary",
                    amount=Decimal("3000"),
                    percentage=Decimal("100"),
                    account_id="income-1",
                ),
            ],
            total=Decimal("3000"),
            currency="EUR",
        )

        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Rent",
                    amount=Decimal("1000"),
                    percentage=Decimal("100"),
                    account_id="expense-1",
                ),
            ],
            total=Decimal("1000"),
            currency="EUR",
            category_count=1,
        )

        query = SankeyQuery(port)
        result = await query.execute()

        # All nodes should have colors
        for node in result.nodes:
            assert node.color is not None
            assert node.color.startswith("#")


class TestSankeyQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = SankeyQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
