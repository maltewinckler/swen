"""Unit tests for TopExpensesQuery (CQRS wrapper)."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import TopExpensesResult
from swen.application.queries.analytics import TopExpensesQuery


class TestTopExpensesQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = TopExpensesResult(
            period_label="Last 3 months",
            items=[],
            total_spending=Decimal("0"),
            currency="EUR",
            months_analyzed=3,
        )
        port.top_expenses.return_value = expected

        query = TopExpensesQuery(port)
        result = await query.execute(
            months=2,
            top_n=7,
            end_month="2024-12",
            include_drafts=True,
        )

        assert result is expected
        port.top_expenses.assert_awaited_once_with(
            months=2,
            top_n=7,
            end_month="2024-12",
            include_drafts=True,
        )


class TestTopExpensesQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = TopExpensesQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
