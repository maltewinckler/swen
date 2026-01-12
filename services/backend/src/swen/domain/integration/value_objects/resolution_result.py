"""Resolution result value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from swen.domain.integration.value_objects.ai_counter_account import (
    AICounterAccountResult,
)
from swen.domain.integration.value_objects.counter_account_rule import (
    CounterAccountRule,
)

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account


@dataclass
class ResolutionResult:
    """Result from the counter-account resolution process."""

    account: Optional[Account]
    ai_result: Optional[AICounterAccountResult] = None
    source: Optional[str] = None  # "rule", "ai", "ai_low_confidence", or "none"

    @property
    def is_resolved(self) -> bool:
        return self.account is not None

    @property
    def is_from_rule(self) -> bool:
        return self.source == "rule"

    @property
    def is_from_ai(self) -> bool:
        return self.source == "ai"

    @property
    def has_ai_result(self) -> bool:
        return self.ai_result is not None

    @property
    def is_ai_low_confidence(self) -> bool:
        return self.source == "ai_low_confidence"


@dataclass
class CounterAccountSuggestion:
    """A suggested Counter-Account for a bank transaction."""

    account: Account
    rule: Optional[CounterAccountRule]
    confidence: float
    reason: str
    source: str = "rule"  # "rule" or "ai"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(msg)

        valid_sources = {"rule", "ai"}
        if self.source not in valid_sources:
            msg = f"source must be one of {valid_sources}, got '{self.source}'"
            raise ValueError(msg)
