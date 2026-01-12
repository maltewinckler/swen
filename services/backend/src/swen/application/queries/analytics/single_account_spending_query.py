"""Single account spending over time query."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.dtos.analytics import TimeSeriesResult
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class SingleAccountSpendingQuery:
    """Return monthly spending totals for one expense account."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SingleAccountSpendingQuery:
        return cls(analytics_read_port=factory.analytics_read_port())

    async def execute(
        self,
        account_id: UUID,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        return await self._analytics.single_account_spending_over_time(
            account_id=account_id,
            months=months,
            end_month=end_month,
            include_drafts=include_drafts,
        )
