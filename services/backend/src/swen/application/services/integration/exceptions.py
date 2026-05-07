"""Exceptions for integration sync services."""

from __future__ import annotations


class InactiveMappingError(Exception):
    """Raised when sync is attempted on an inactive account mapping."""
