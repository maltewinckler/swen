"""Get user settings query."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.settings.dtos import UserSettingsDTO
from swen.domain.settings import UserSettingsRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class GetUserSettingsQuery:
    """Query to get user settings (creates defaults if not exists)."""

    def __init__(self, settings_repo: UserSettingsRepository):
        self._settings_repo = settings_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> GetUserSettingsQuery:
        return cls(settings_repo=factory.user_settings_repository())

    async def execute(self) -> UserSettingsDTO:
        settings = await self._settings_repo.get_or_create()
        return UserSettingsDTO.from_user_settings(settings)
