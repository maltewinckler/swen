"""SWEN Identity - User management, authentication, and authorization.

This module handles all identity-related concerns:
- User management (CRUD, roles)
- Authentication (login, registration, tokens)
- Authorization (role-based access control)
- Password management (hashing, reset)
- Email notifications (password reset)

Settings/preferences are handled by swen.domain.settings.
The core SWEN domain (accounting, banking) only references user_id,
keeping identity concerns separated.
"""

from swen_identity.application.context import UserContext
from swen_identity.domain import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    Email,
    EmailAlreadyExistsError,
    InvalidEmailError,
    PasswordResetToken,
    PasswordResetTokenRepository,
    TokenPayload,
    User,
    UserCredential,
    UserCredentialRepository,
    UserNotFoundError,
    UserRepository,
    UserRole,
)
from swen_identity.domain.ports import (
    EmailNotificationPort,
    PasswordHashingPort,
    TokenHandlingPort,
)
from swen_identity.domain.services import (
    AuthenticationService,
    PasswordResetService,
)
from swen_identity.exceptions import (
    AccountLockedError,
    AuthError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidResetTokenError,
    InvalidTokenError,
    PasswordResetRateLimitError,
    RefreshTokenExpiredError,
    WeakPasswordError,
)

__all__ = [
    # Domain - User
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
    # Exceptions
    "AccountLockedError",
    "AuthError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "InvalidResetTokenError",
    "InvalidTokenError",
    "PasswordResetRateLimitError",
    "RefreshTokenExpiredError",
    "WeakPasswordError",
    # Ports
    "EmailNotificationPort",
    "PasswordHashingPort",
    "TokenHandlingPort",
    # Application Context
    "UserContext",
    # Domain Services
    "AuthenticationService",
    "PasswordResetService",
]
