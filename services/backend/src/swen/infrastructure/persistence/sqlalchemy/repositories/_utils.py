"""Shared utilities for SQLAlchemy repositories."""

from uuid import UUID


def ensure_uuid(value: UUID | str | None) -> UUID | None:
    """
    Ensure a value is a UUID, converting from string if necessary.

    This handles the common case where user_id flows through the system
    as either a UUID or a string representation of a UUID.
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    msg = f"Expected UUID or str, got {type(value).__name__}"
    raise TypeError(msg)
