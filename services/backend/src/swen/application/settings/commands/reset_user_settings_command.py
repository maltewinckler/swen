"""Reset user settings to defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.ports.unit_of_work import UnitOfWork
from swen.application.settings.dtos import UserSettingsDTO
from swen.domain.settings import UserSettingsRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class ResetUserSettingsCommand:
    """Reset all settings to defaults for the current user."""

    def __init__(self, settings_repo: UserSettingsRepository, uow: UnitOfWork):
        self._settings_repo = settings_repo
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ResetUserSettingsCommand:
        return cls(
            settings_repo=factory.user_settings_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self) -> UserSettingsDTO:
        async with self._uow:
            settings = await self._settings_repo.get_or_create()
            settings.reset()
            await self._settings_repo.save(settings)
            return UserSettingsDTO.from_user_settings(settings)
