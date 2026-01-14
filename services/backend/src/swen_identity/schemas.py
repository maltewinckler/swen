"""Identity schemas and data structures.

These are simple data classes used for transferring identity
data between components.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT token payload.

    This represents the data extracted from a verified JWT token.

    Attributes
    ----------
    user_id
        The unique identifier of the user
    email
        The user's email address
    exp
        Token expiration timestamp
    token_type
        Either "access" or "refresh"
    """

    user_id: UUID
    email: str
    exp: datetime
    token_type: str  # "access" or "refresh"

    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(tz=self.exp.tzinfo) > self.exp

    def is_access_token(self) -> bool:
        """Check if this is an access token."""
        return self.token_type == "access"

    def is_refresh_token(self) -> bool:
        """Check if this is a refresh token."""
        return self.token_type == "refresh"
