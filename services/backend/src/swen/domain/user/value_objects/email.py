"""Email value object.

Provides validated, normalized email addresses for user identification.
"""

import re
from dataclasses import dataclass

from swen.domain.user.exceptions import InvalidEmailError

# Simple but effective email regex
# Validates: user@domain.tld (minimum requirements)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email:
    """Value object representing a validated email address."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            msg = "Email cannot be empty"
            raise InvalidEmailError(msg)

        normalized = self.value.lower().strip()

        if not EMAIL_PATTERN.match(normalized):
            msg = f"Invalid email format: {self.value}"
            raise InvalidEmailError(msg)

        # Replace value with normalized version (frozen dataclass workaround)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email('{self.value}')"
