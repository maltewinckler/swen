"""Sankey diagram DTOs for cash flow visualization."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SankeyNode(BaseModel):
    """A node in the Sankey diagram.

    Nodes represent either income sources, a central 'Total Income' node,
    expense categories, or savings.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    category: str = ""  # "income" | "total" | "expense" | "savings"
    color: str | None = None


class SankeyLink(BaseModel):
    """A link (flow) between two nodes in the Sankey diagram."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    value: Decimal


class SankeyData(BaseModel):
    """Complete data structure for a Sankey diagram."""

    nodes: list[SankeyNode] = []
    links: list[SankeyLink] = []
    currency: str = "EUR"
    period_label: str = ""
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_savings: Decimal = Decimal("0")
