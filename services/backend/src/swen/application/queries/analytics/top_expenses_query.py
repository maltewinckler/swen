"""Fetch top expense categories via analytics port."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.analytics import TopExpensesResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class TopExpensesQuery:
    """Return ranked expense categories for a period."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> TopExpensesQuery:
        return cls(analytics_read_port=factory.analytics_read_port())

    async def execute(
        self,
        months: int = 3,
        top_n: int = 10,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TopExpensesResult:
        return await self._analytics.top_expenses(
            months=months,
            top_n=top_n,
            end_month=end_month,
            include_drafts=include_drafts,
        )
