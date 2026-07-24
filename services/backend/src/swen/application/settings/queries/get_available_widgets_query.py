"""Get available dashboard widgets query."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.settings.dtos import AvailableWidgetsDTO
from swen.domain.settings import UserSettingsRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class GetAvailableWidgetsQuery:
    """Query for the dashboard widget catalog and the current user's widget state."""

    def __init__(self, settings_repo: UserSettingsRepository):
        self._settings_repo = settings_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> GetAvailableWidgetsQuery:
        return cls(settings_repo=factory.user_settings_repository())

    async def execute(self) -> AvailableWidgetsDTO:
        settings = await self._settings_repo.get_or_create()
        return AvailableWidgetsDTO.from_user_settings(settings)
