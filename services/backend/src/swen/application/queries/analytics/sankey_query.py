"""Build Sankey cash-flow data from income and spending breakdowns."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.dtos.analytics.sankey_dto import (
    SankeyData,
    SankeyLink,
    SankeyNode,
)
from swen.application.ports.analytics import AnalyticsReadPort

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


# Color palette for Sankey nodes
INCOME_COLORS = [
    "#22c55e",  # green-500
    "#16a34a",  # green-600
    "#15803d",  # green-700
    "#10b981",  # emerald-500
    "#059669",  # emerald-600
]

EXPENSE_COLORS = [
    "#f97316",  # orange-500
    "#ef4444",  # red-500
    "#f59e0b",  # amber-500
    "#ec4899",  # pink-500
    "#8b5cf6",  # violet-500
    "#6366f1",  # indigo-500
    "#14b8a6",  # teal-500
    "#3b82f6",  # blue-500
    "#d946ef",  # fuchsia-500
    "#84cc16",  # lime-500
]

TOTAL_COLOR = "#6b7280"  # gray-500
SAVINGS_COLOR = "#22c55e"  # green-500 (positive savings)
DEFICIT_COLOR = "#ef4444"  # red-500 (negative savings)


class SankeyQuery:
    """Generate Sankey nodes/links for income → spending → savings."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
    ):
        self._analytics = analytics_read_port

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SankeyQuery:
        return cls(
            analytics_read_port=factory.analytics_read_port(),
        )

    async def execute(
        self,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> SankeyData:
        income_result = await self._analytics.income_breakdown(
            month=month,
            days=days,
            include_drafts=include_drafts,
        )
        spending_result = await self._analytics.spending_breakdown(
            month=month,
            days=days,
            include_drafts=include_drafts,
        )

        nodes: list[SankeyNode] = []
        links: list[SankeyLink] = []

        for idx, item in enumerate(income_result.items):
            node_id = f"income_{item.account_id}"
            nodes.append(
                SankeyNode(
                    id=node_id,
                    label=item.category,
                    category="income",
                    color=INCOME_COLORS[idx % len(INCOME_COLORS)],
                ),
            )
            links.append(
                SankeyLink(
                    source=node_id,
                    target="total",
                    value=item.amount,
                ),
            )

        nodes.append(
            SankeyNode(
                id="total",
                label="Total Income",
                category="total",
                color=TOTAL_COLOR,
            ),
        )

        for idx, item in enumerate(spending_result.items):
            node_id = f"expense_{item.account_id}"
            nodes.append(
                SankeyNode(
                    id=node_id,
                    label=item.category,
                    category="expense",
                    color=EXPENSE_COLORS[idx % len(EXPENSE_COLORS)],
                ),
            )
            links.append(
                SankeyLink(
                    source="total",
                    target=node_id,
                    value=item.amount,
                ),
            )

        net_savings = income_result.total - spending_result.total

        if net_savings > Decimal("0"):
            nodes.append(
                SankeyNode(
                    id="savings",
                    label="Savings",
                    category="savings",
                    color=SAVINGS_COLOR,
                ),
            )
            links.append(
                SankeyLink(
                    source="total",
                    target="savings",
                    value=net_savings,
                ),
            )

        return SankeyData(
            nodes=nodes,
            links=links,
            currency=income_result.currency,
            period_label=income_result.period_label,
            total_income=income_result.total,
            total_expenses=spending_result.total,
            net_savings=net_savings,
        )
