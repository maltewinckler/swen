"""Unit tests for IncomeBreakdownQuery (CQRS wrapper)."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.dtos.analytics import IncomeBreakdownResult
from swen.application.queries.analytics import IncomeBreakdownQuery


class TestIncomeBreakdownQuery:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        port = AsyncMock()
        expected = IncomeBreakdownResult(
            period_label="December 2024",
            items=[],
            total=Decimal("0"),
            currency="EUR",
        )
        port.income_breakdown.return_value = expected

        query = IncomeBreakdownQuery(port)
        result = await query.execute(month="2024-12", days=None, include_drafts=True)

        assert result is expected
        port.income_breakdown.assert_awaited_once_with(
            month="2024-12",
            days=None,
            include_drafts=True,
        )


class TestIncomeBreakdownQueryDependencyInjection:
    """Tests for dependency injection patterns."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()

        query = IncomeBreakdownQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
