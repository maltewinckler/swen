"""Password reset token aggregate.

Its own aggregate rather than a child of ``User``: many tokens accumulate
per user over time (rate-limiting counts recent ones, requesting a new
reset invalidates old ones), and none of that has any invariant shared
with ``User``'s own state.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PasswordResetToken(BaseModel):
    """Immutable password reset token data."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Check if the token has expired."""
        return now > self.expires_at

    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None
