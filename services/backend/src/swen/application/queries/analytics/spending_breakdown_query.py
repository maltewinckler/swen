"""Fetch spending breakdown by category via analytics port."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.analytics import SpendingBreakdownResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class SpendingBreakdownQuery:
    """Return spending breakdown by category."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SpendingBreakdownQuery:
        return cls(analytics_read_port=factory.analytics_read_port())

    async def execute(
        self,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> SpendingBreakdownResult:
        return await self._analytics.spending_breakdown(
            month=month,
            days=days,
            include_drafts=include_drafts,
        )
