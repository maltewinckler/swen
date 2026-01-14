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

# Domain - User aggregate and value objects
# Application Context
from swen_identity.application.context import UserContext

# Application Services
from swen_identity.application.services import (
    AuthenticationService,
    PasswordResetService,
)
from swen_identity.domain.user import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    Email,
    EmailAlreadyExistsError,
    InvalidEmailError,
    User,
    UserNotFoundError,
    UserRepository,
    UserRole,
)

# Auth exceptions
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

# Repositories (abstract)
from swen_identity.repositories import (
    PasswordResetTokenData,
    PasswordResetTokenRepository,
    UserCredentialData,
    UserCredentialRepository,
)

# Schemas
from swen_identity.schemas import TokenPayload

# Services
from swen_identity.services import (
    JWTService,
    PasswordHashingService,
)

__all__ = [
    # Domain - User
    "CannotDeleteSelfError",
    "CannotDemoteSelfError",
    "Email",
    "EmailAlreadyExistsError",
    "InvalidEmailError",
    "User",
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
    # Repositories
    "PasswordResetTokenData",
    "PasswordResetTokenRepository",
    "UserCredentialData",
    "UserCredentialRepository",
    # Schemas
    "TokenPayload",
    # Services
    "JWTService",
    "PasswordHashingService",
    # Application Context
    "UserContext",
    # Application Services
    "AuthenticationService",
    "PasswordResetService",
]
