"""Domain layer for identity management.

This domain handles:
- User aggregate (identity: id, email, role)
- User authentication and authorization
- Multi-user support

Settings/preferences are handled by swen.domain.settings.
"""

from swen_identity.domain.aggregates import (
    PasswordResetToken,
    User,
    UserCredential,
)
from swen_identity.domain.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    EmailAlreadyExistsError,
    InvalidEmailError,
    UserNotFoundError,
)
from swen_identity.domain.repositories import (
    PasswordResetTokenRepository,
    UserCredentialRepository,
    UserRepository,
)
from swen_identity.domain.value_objects import (
    Email,
    TokenPayload,
    UserRole,
)

__all__ = [
    "CannotDeleteSelfError",
    "CannotDemoteSelfError",
    "Email",
    "EmailAlreadyExistsError",
    "InvalidEmailError",
    "PasswordResetToken",
    "PasswordResetTokenRepository",
    "TokenPayload",
    "User",
    "UserCredential",
    "UserCredentialRepository",
    "UserNotFoundError",
    "UserRepository",
    "UserRole",
]
