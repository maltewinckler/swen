"""Unit tests for SpendingBreakdownQuery (CQRS wrapper)."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import SpendingBreakdownResult
from swen.application.queries.analytics import SpendingBreakdownQuery


class TestSpendingBreakdownQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = SpendingBreakdownResult(
            period_label="December 2024",
            items=[],
            total=Decimal("0"),
            currency="EUR",
            category_count=0,
        )
        port.spending_breakdown.return_value = expected

        query = SpendingBreakdownQuery(port)
        result = await query.execute(month="2024-12", days=None, include_drafts=True)

        assert result is expected
        port.spending_breakdown.assert_awaited_once_with(
            month="2024-12",
            days=None,
            include_drafts=True,
        )


class TestSpendingBreakdownQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = SpendingBreakdownQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
