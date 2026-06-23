"""Sankey diagram DTOs for cash flow visualization."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SankeyNode:
    """A node in the Sankey diagram.

    Nodes represent either income sources, a central 'Total Income' node,
    expense categories, or savings.
    """

    id: str
    label: str
    category: str  # "income" | "total" | "expense" | "savings"
    color: str | None = None


@dataclass(frozen=True)
class SankeyLink:
    """A link (flow) between two nodes in the Sankey diagram."""

    source: str
    target: str
    value: Decimal


@dataclass
class SankeyData:
    """Complete data structure for a Sankey diagram."""

    nodes: list[SankeyNode] = field(default_factory=list)
    links: list[SankeyLink] = field(default_factory=list)
    currency: str = "EUR"
    period_label: str = ""
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_savings: Decimal = Decimal("0")
