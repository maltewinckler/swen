"""User settings domain - application preferences for swen."""

from swen.domain.settings.aggregates import UserSettings
from swen.domain.settings.repositories import UserSettingsRepository
from swen.domain.settings.value_objects import (
    AVAILABLE_WIDGETS,
    DEFAULT_ENABLED_WIDGETS,
    AISettings,
    DashboardSettings,
    DisplaySettings,
    SyncSettings,
)

__all__ = [
    "AVAILABLE_WIDGETS",
    "AISettings",
    "DashboardSettings",
    "DEFAULT_ENABLED_WIDGETS",
    "DisplaySettings",
    "SyncSettings",
    "UserSettings",
    "UserSettingsRepository",
]
