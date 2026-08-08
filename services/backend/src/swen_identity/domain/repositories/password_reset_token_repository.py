"""Abstract repository interface for password reset tokens."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from swen_identity.domain.aggregates.password_reset_token import (
    PasswordResetToken,
)


class PasswordResetTokenRepository(ABC):
    """Abstract repository for password reset tokens."""

    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        """Create a new password reset token.

        Parameters
        ----------
        user_id
            The user's unique identifier
        token_hash
            SHA-256 hash of the raw token
        expires_at
            When the token expires

        Returns
        -------
        The token's unique identifier
        """

    @abstractmethod
    async def find_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        """Find a valid (unused) token by its hash.

        Parameters
        ----------
        token_hash
            SHA-256 hash of the raw token

        Returns
        -------
        Token data if found and not used, None otherwise
        """

    @abstractmethod
    async def mark_used(self, token_id: UUID) -> None:
        """Mark a token as used.

        Parameters
        ----------
        token_id
            The token's unique identifier
        """

    @abstractmethod
    async def invalidate_all_for_user(self, user_id: UUID) -> None:
        """Invalidate all tokens for a user (e.g., when requesting a new one).

        Parameters
        ----------
        user_id
            The user's unique identifier
        """

    @abstractmethod
    async def count_recent_for_user(self, user_id: UUID, since: datetime) -> int:
        """Count tokens created for a user since a given time (for rate limiting).

        Parameters
        ----------
        user_id
            The user's unique identifier
        since
            Count tokens created after this time

        Returns
        -------
        Number of tokens created since the given time
        """

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired tokens from the database.

        Returns
        -------
        Number of tokens deleted
        """
