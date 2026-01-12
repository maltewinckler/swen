"""Secure string value object for sensitive data."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


@dataclass(frozen=True)
class SecureString:
    """
    Value object that wraps sensitive string data.

    Prevents accidental exposure through:
    - String representation (__str__, __repr__)
    - Logging
    - Debugging tools
    - Error messages

    The actual value is only accessible via explicit get_value() call.
    """

    _value: str

    def __post_init__(self):
        """Validate that value is not empty."""
        if not isinstance(self._value, str):
            msg = "SecureString value must be a string"
            raise TypeError(msg)

        if not self._value:
            msg = "SecureString cannot be empty"
            raise ValueError(msg)

    def get_value(self) -> str:
        """
        Get the actual sensitive value.

        This is the ONLY way to access the real value.
        The explicit method name makes it clear that sensitive data is accessed.
        """
        return self._value

    def __str__(self) -> str:
        """Return masked representation."""
        return "*****"

    def __repr__(self) -> str:
        """Return masked representation for debugging."""
        return "SecureString(*****)"

    def __eq__(self, other: object) -> bool:
        """Compare securely without exposing values in error messages."""
        if not isinstance(other, SecureString):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Allow use in sets/dicts."""
        return hash(self._value)

    def __len__(self) -> int:
        """Return length without exposing value."""
        return len(self._value)

    def matches(self, other: str) -> bool:
        """
        Check if the secure string matches a plain string.

        Useful for validation without exposing the value.
        """
        return self._value == other

    def is_empty(self) -> bool:
        """Check if empty without exposing value."""
        return len(self._value) == 0

    @classmethod
    def from_env(cls, env_var_name: str) -> "SecureString":
        """
        Create SecureString from environment variable.

        Raises ValueError if not found.
        """
        value = os.getenv(env_var_name)
        if value is None:
            msg = f"Environment variable {env_var_name} not found"
            raise ValueError(msg)
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """
        Make SecureString natively compatible with Pydantic v2.

        This allows SecureString to be used in Pydantic models without
        requiring arbitrary_types_allowed=True in model configuration.

        The schema validates that the input is a non-empty string and
        wraps it in a SecureString instance.
        """
        return core_schema.no_info_plain_validator_function(
            cls._pydantic_validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda _: "*****",  # Always serialize as masked
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def _pydantic_validate(cls, value: Any) -> SecureString:
        """
        Pydantic validation method.

        Parameters
        ----------
        value
            The value to validate (string or SecureString instance)

        Returns
        -------
        SecureString instance

        Raises
        ------
        TypeError
            If value is not a string or SecureString
        ValueError
            If value is empty (handled by core_schema.str_schema min_length)
        """
        # If already a SecureString, return as-is
        if isinstance(value, cls):
            return value

        # Validate type
        if not isinstance(value, str):
            msg = "SecureString value must be a string"
            raise TypeError(msg)

        # Empty check is handled by core_schema.str_schema(min_length=1)
        # but we add explicit check for clarity
        if not value:
            msg = "SecureString cannot be empty"
            raise ValueError(msg)

        return cls(value)
