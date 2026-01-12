"""Fetch spending over time via the analytics read port."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.analytics import CategoryTimeSeriesResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class SpendingOverTimeQuery:
    """Return monthly spending totals by expense category."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SpendingOverTimeQuery:
        return cls(analytics_read_port=factory.analytics_read_port())

    async def execute(
        self,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> CategoryTimeSeriesResult:
        return await self._analytics.spending_over_time(
            months=months,
            end_month=end_month,
            include_drafts=include_drafts,
        )
