"""Value objects for user settings."""

from swen.domain.settings.value_objects.ai_settings import AISettings
from swen.domain.settings.value_objects.dashboard_settings import (
    AVAILABLE_WIDGETS,
    DEFAULT_ENABLED_WIDGETS,
    DashboardSettings,
)
from swen.domain.settings.value_objects.display_settings import DisplaySettings
from swen.domain.settings.value_objects.sync_settings import SyncSettings

__all__ = [
    "AVAILABLE_WIDGETS",
    "AISettings",
    "DashboardSettings",
    "DEFAULT_ENABLED_WIDGETS",
    "DisplaySettings",
    "SyncSettings",
]
