"""Unit tests for SpendingOverTimeQuery (CQRS wrapper)."""

from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import CategoryTimeSeriesResult
from swen.application.queries.analytics import SpendingOverTimeQuery


class TestSpendingOverTimeQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = CategoryTimeSeriesResult(
            data_points=[],
            categories=[],
            currency="EUR",
            totals_by_category={},
        )
        port.spending_over_time.return_value = expected

        query = SpendingOverTimeQuery(port)
        result = await query.execute(months=2, end_month="2024-12", include_drafts=True)

        assert result is expected
        port.spending_over_time.assert_awaited_once_with(
            months=2,
            end_month="2024-12",
            include_drafts=True,
        )


class TestSpendingOverTimeQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = SpendingOverTimeQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
