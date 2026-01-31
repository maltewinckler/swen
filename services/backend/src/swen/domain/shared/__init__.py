"""Shared domain components.

This module exports shared value objects, exceptions, and base classes
used across domain boundaries.
"""

# Re-export all exceptions from the exceptions module
from swen.domain.shared.exceptions import (
    BusinessRuleViolation,
    ConcurrencyError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    ErrorCode,
    ValidationError,
)
from swen.domain.shared.time import today_utc, utc_now

__all__ = [
    # Error codes
    "ErrorCode",
    # Base exception
    "DomainException",
    # Exception categories
    "ValidationError",
    "BusinessRuleViolation",
    "EntityNotFoundError",
    "ConflictError",
    "ConcurrencyError",
    # Utilities
    "today_utc",
    "utc_now",
]
