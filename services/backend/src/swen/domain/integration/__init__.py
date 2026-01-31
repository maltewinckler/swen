"""Integration domain for cross-domain orchestration."""

from swen.domain.integration.entities import (
    AccountMapping,
    TransactionImport,
)
from swen.domain.integration.services import (
    CounterAccountResolutionService,
)
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
    CounterAccountRule,
    CounterAccountSuggestion,
    ImportStatus,
    PatternType,
    ResolutionResult,
    RuleSource,
)

__all__ = [
    # Entities
    "AccountMapping",
    "TransactionImport",
    # Services
    "CounterAccountResolutionService",
    # Value Objects
    "AICounterAccountResult",
    "CounterAccountOption",
    "CounterAccountRule",
    "CounterAccountSuggestion",
    "ImportStatus",
    "PatternType",
    "ResolutionResult",
    "RuleSource",
]
