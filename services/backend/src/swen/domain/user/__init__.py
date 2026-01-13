"""User domain - manages user identity and preferences.

This domain handles:
- User aggregate (identity, preferences)
- User preferences (sync settings, display settings)
- Multi-user support

Design notes:
- User ID is a random UUID4 generated at creation (opaque, unpredictable)
- Email is a mutable attribute, indexed for lookups
- Preferences are value objects embedded in User aggregate
- Repository interface defined here, implementation in infrastructure
"""

from swen.domain.user.aggregates import User
from swen.domain.user.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    EmailAlreadyExistsError,
    InvalidEmailError,
    UserNotFoundError,
)
from swen.domain.user.repositories import UserRepository
from swen.domain.user.value_objects import (
    AVAILABLE_WIDGETS,
    DEFAULT_ENABLED_WIDGETS,
    AISettings,
    DashboardSettings,
    DisplaySettings,
    Email,
    SyncSettings,
    UserPreferences,
    UserRole,
)

__all__ = [
    "AISettings",
    "AVAILABLE_WIDGETS",
    "CannotDeleteSelfError",
    "CannotDemoteSelfError",
    "DEFAULT_ENABLED_WIDGETS",
    "DashboardSettings",
    "DisplaySettings",
    "Email",
    "EmailAlreadyExistsError",
    "InvalidEmailError",
    "SyncSettings",
    "User",
    "UserNotFoundError",
    "UserPreferences",
    "UserRepository",
    "UserRole",
]
