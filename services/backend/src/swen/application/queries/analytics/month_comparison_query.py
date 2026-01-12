"""Month comparison query."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.analytics import MonthComparisonResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class MonthComparisonQuery:
    """Compare current vs previous month for income/spending metrics."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> MonthComparisonQuery:
        return cls(analytics_read_port=factory.analytics_read_port())

    async def execute(
        self,
        month: str | None = None,
        include_drafts: bool = False,
    ) -> MonthComparisonResult:
        return await self._analytics.month_comparison(
            month=month,
            include_drafts=include_drafts,
        )
