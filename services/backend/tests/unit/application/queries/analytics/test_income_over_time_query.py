"""Unit tests for IncomeOverTimeQuery (CQRS wrapper)."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import TimeSeriesResult
from swen.application.queries.analytics import IncomeOverTimeQuery


class TestIncomeOverTimeQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = TimeSeriesResult(
            data_points=[],
            currency="EUR",
            total=Decimal("0"),
            average=Decimal("0"),
            min_value=Decimal("0"),
            max_value=Decimal("0"),
        )
        port.income_over_time.return_value = expected

        query = IncomeOverTimeQuery(port)
        result = await query.execute(months=2, end_month="2024-12", include_drafts=True)

        assert result is expected
        port.income_over_time.assert_awaited_once_with(
            months=2,
            end_month="2024-12",
            include_drafts=True,
        )


class TestIncomeOverTimeQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = IncomeOverTimeQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()

