"""Email value object.

Provides validated, normalized email addresses for user identification.
"""

import re

from pydantic import BaseModel, ConfigDict, field_validator

from swen_identity.domain.user.exceptions import InvalidEmailError

# Simple but effective email regex
# Validates: user@domain.tld (minimum requirements)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class Email(BaseModel):
    """Value object representing a validated email address."""

    model_config = ConfigDict(frozen=True)

    value: str

    @field_validator("value", mode="after")
    @classmethod
    def _validate_and_normalize(cls, value: str) -> str:
        if not value:
            msg = "Email cannot be empty"
            raise InvalidEmailError(msg)

        normalized = value.lower().strip()

        if not EMAIL_PATTERN.match(normalized):
            msg = f"Invalid email format: {value}"
            raise InvalidEmailError(msg)

        return normalized

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email('{self.value}')"
