"""AI Counter-Account resolution value objects."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class AICounterAccountResult:
    """Result from AI-based counter-account resolution."""

    counter_account_id: UUID
    confidence: float  # 0.0 - 1.0
    reasoning: Optional[str] = None
    tier: Optional[str] = None  # e.g., "pattern", "example", "nli", "fallback"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(msg)

    def is_confident(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold


@dataclass(frozen=True)
class CounterAccountOption:
    """
    Available Counter-Account information for AI prompt context.

    This value object provides the AI with information about an available
    account that could be used as a Counter-Account. It contains the
    essential fields needed for the AI to make an informed decision.
    """

    account_id: UUID
    account_number: str
    name: str
    account_type: str  # "expense" or "income"
    description: Optional[str] = None

    def __post_init__(self) -> None:
        valid_types = {"expense", "income"}
        if self.account_type not in valid_types:
            msg = (
                f"account_type must be one of {valid_types}, got '{self.account_type}'"
            )
            raise ValueError(msg)

    @property
    def display_label(self) -> str:
        return f"[{self.account_number}] {self.name}"

    @property
    def display_label_with_description(self) -> str:
        base = f"[{self.account_number}] {self.name} ({self.account_type.upper()})"
        if self.description:
            return f"{base}\n  → {self.description}"
        return base
