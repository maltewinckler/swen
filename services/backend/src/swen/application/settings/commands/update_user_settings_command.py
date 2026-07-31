"""Update user settings with partial fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.ports.unit_of_work import UnitOfWork
from swen.application.settings.dtos import UserSettingsDTO, UserSettingsUpdateDTO
from swen.domain.settings import (
    AVAILABLE_WIDGETS,
    UserSettingsRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateUserSettingsCommand:
    """Update user settings for the current user."""

    def __init__(self, settings_repo: UserSettingsRepository, uow: UnitOfWork):
        self._settings_repo = settings_repo
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateUserSettingsCommand:
        return cls(
            settings_repo=factory.user_settings_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, updates: UserSettingsUpdateDTO) -> UserSettingsDTO:
        # Validate that at least one setting is provided
        if updates.is_empty():
            msg = "At least one setting must be specified for update"
            raise ValueError(msg)

        # Validate widget IDs
        if updates.enabled_widgets is not None:
            invalid_widgets = set(updates.enabled_widgets) - set(AVAILABLE_WIDGETS)
            if invalid_widgets:
                msg = f"Invalid widget IDs: {invalid_widgets}"
                raise ValueError(msg)

        if updates.widget_settings is not None:
            invalid_settings = set(updates.widget_settings) - set(AVAILABLE_WIDGETS)
            if invalid_settings:
                msg = f"Widget settings reference invalid widgets: {invalid_settings}"
                raise ValueError(msg)

        async with self._uow:
            # Get or create settings
            settings = await self._settings_repo.get_or_create()

            # Apply updates
            settings.update_sync(
                auto_post_transactions=updates.auto_post_transactions,
                default_currency=updates.default_currency,
            )
            settings.update_display(
                show_draft_transactions=updates.show_draft_transactions,
                default_date_range_days=updates.default_date_range_days,
            )
            settings.update_dashboard(
                enabled_widgets=updates.enabled_widgets,
                widget_settings=updates.widget_settings,
            )
            settings.update_ai(
                enabled=updates.ai_enabled,
                model_name=updates.ai_model_name,
                min_confidence=updates.ai_min_confidence,
            )

            await self._settings_repo.save(settings)
            return UserSettingsDTO.from_user_settings(settings)
