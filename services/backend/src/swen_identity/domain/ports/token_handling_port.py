"""Port for issuing and verifying authentication tokens.

Deliberately technology-agnostic: the current implementation is JWT, but
nothing in the application layer should need to know that.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from swen_identity.domain.value_objects.token_payload import TokenPayload


class TokenHandlingPort(ABC):
    """Port for creating and verifying access/refresh tokens."""

    @abstractmethod
    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a short-lived access token."""

    @abstractmethod
    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a long-lived refresh token."""

    @abstractmethod
    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a token, raising if invalid, expired, or malformed."""
