"""Reset user settings to defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.domain.settings import UserSettings, UserSettingsRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class ResetUserSettingsCommand:
    """Reset all settings to defaults for the current user."""

    def __init__(self, settings_repo: UserSettingsRepository):
        self._settings_repo = settings_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ResetUserSettingsCommand:
        return cls(settings_repo=factory.user_settings_repository())

    async def execute(self) -> UserSettings:
        settings = await self._settings_repo.get_or_create()
        settings.reset()
        await self._settings_repo.save(settings)
        return settings
