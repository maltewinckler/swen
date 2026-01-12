"""Value objects for the user domain."""

from swen.domain.user.value_objects.ai_settings import AISettings
from swen.domain.user.value_objects.dashboard_settings import (
    AVAILABLE_WIDGETS,
    DEFAULT_ENABLED_WIDGETS,
    DashboardSettings,
)
from swen.domain.user.value_objects.display_settings import DisplaySettings
from swen.domain.user.value_objects.email import Email
from swen.domain.user.value_objects.sync_settings import SyncSettings
from swen.domain.user.value_objects.user_preferences import UserPreferences

__all__ = [
    "AISettings",
    "AVAILABLE_WIDGETS",
    "DEFAULT_ENABLED_WIDGETS",
    "DashboardSettings",
    "DisplaySettings",
    "Email",
    "SyncSettings",
    "UserPreferences",
]

