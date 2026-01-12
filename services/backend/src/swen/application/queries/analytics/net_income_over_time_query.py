"""Net income over time query."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.analytics import TimeSeriesResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class NetIncomeOverTimeQuery:
    """Return monthly net income values."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> NetIncomeOverTimeQuery:
        return cls(
            analytics_read_port=factory.analytics_read_port(),
        )

    async def execute(
        self,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        return await self._analytics.net_income_over_time(
            months=months,
            end_month=end_month,
            include_drafts=include_drafts,
        )
