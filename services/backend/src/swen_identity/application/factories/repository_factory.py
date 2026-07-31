"""Repository factory protocol for swen_identity's application layer."""

from __future__ import annotations

from typing import Protocol

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.domain.user.repositories import UserRepository
from swen_identity.repositories import (
    PasswordResetTokenRepository,
    UserCredentialRepository,
)


class RepositoryFactory(Protocol):
    """Protocol for creating swen_identity repositories."""

    def unit_of_work(self) -> UnitOfWork:
        """Get a unit-of-work scoped to the current request session."""
        ...

    def user_repository(self) -> UserRepository:
        """Get user repository."""
        ...

    def user_credential_repository(self) -> UserCredentialRepository:
        """Get user credential repository."""
        ...

    def password_reset_token_repository(self) -> PasswordResetTokenRepository:
        """Get password reset token repository."""
        ...
