"""Unit tests for MonthComparisonQuery (CQRS wrapper)."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from swen.application.dtos.analytics import MonthComparisonResult
from swen.application.queries.analytics import MonthComparisonQuery


class TestMonthComparisonQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = MonthComparisonResult(
            current_month="December 2024",
            previous_month="November 2024",
            currency="EUR",
            current_income=Decimal("0"),
            previous_income=Decimal("0"),
            income_change=Decimal("0"),
            income_change_percentage=Decimal("0"),
            current_spending=Decimal("0"),
            previous_spending=Decimal("0"),
            spending_change=Decimal("0"),
            spending_change_percentage=Decimal("0"),
            current_net=Decimal("0"),
            previous_net=Decimal("0"),
            net_change=Decimal("0"),
            net_change_percentage=Decimal("0"),
            category_comparisons=[],
        )
        port.month_comparison.return_value = expected

        query = MonthComparisonQuery(port)
        result = await query.execute(month="2024-12", include_drafts=True)

        assert result is expected
        port.month_comparison.assert_awaited_once_with(
            month="2024-12",
            include_drafts=True,
        )


class TestMonthComparisonQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = MonthComparisonQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
