"""Abstract repository interfaces for identity management."""

from swen_identity.repositories.password_reset_token_repository import (
    PasswordResetTokenData,
    PasswordResetTokenRepository,
)
from swen_identity.repositories.user_credential_repository import (
    UserCredentialData,
    UserCredentialRepository,
)

__all__ = [
    "PasswordResetTokenData",
    "PasswordResetTokenRepository",
    "UserCredentialData",
    "UserCredentialRepository",
]
