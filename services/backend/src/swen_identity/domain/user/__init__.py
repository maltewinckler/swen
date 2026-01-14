"""User domain manages user identity only.

This domain handles:
- User aggregate (identity: id, email, role)
- User authentication and authorization
- Multi-user support

Settings/preferences are handled by swen.domain.settings.
"""

from swen_identity.domain.user.aggregates import User
from swen_identity.domain.user.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    EmailAlreadyExistsError,
    InvalidEmailError,
    UserNotFoundError,
)
from swen_identity.domain.user.repositories import UserRepository
from swen_identity.domain.user.value_objects import (
    Email,
    UserRole,
)

__all__ = [
    "CannotDeleteSelfError",
    "CannotDemoteSelfError",
    "Email",
    "EmailAlreadyExistsError",
    "InvalidEmailError",
    "User",
    "UserNotFoundError",
    "UserRepository",
    "UserRole",
]
