"""Update user settings with partial fields."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from swen.domain.settings import (
    AVAILABLE_WIDGETS,
    UserSettings,
    UserSettingsRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateUserSettingsCommand:
    """Update user settings for the current user."""

    def __init__(self, settings_repo: UserSettingsRepository):
        self._settings_repo = settings_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateUserSettingsCommand:
        return cls(settings_repo=factory.user_settings_repository())

    async def execute(  # NOQA: PLR0913
        self,
        auto_post_transactions: bool | None = None,
        default_currency: str | None = None,
        show_draft_transactions: bool | None = None,
        default_date_range_days: int | None = None,
        enabled_widgets: list[str] | None = None,
        widget_settings: dict[str, dict[str, Any]] | None = None,
        ai_enabled: bool | None = None,
        ai_model_name: str | None = None,
        ai_min_confidence: float | None = None,
    ) -> UserSettings:
        # Validate that at least one setting is provided
        if all(
            v is None
            for v in [
                auto_post_transactions,
                default_currency,
                show_draft_transactions,
                default_date_range_days,
                enabled_widgets,
                widget_settings,
                ai_enabled,
                ai_model_name,
                ai_min_confidence,
            ]
        ):
            msg = "At least one setting must be specified for update"
            raise ValueError(msg)

        # Validate widget IDs
        if enabled_widgets is not None:
            invalid_widgets = set(enabled_widgets) - set(AVAILABLE_WIDGETS.keys())
            if invalid_widgets:
                msg = f"Invalid widget IDs: {invalid_widgets}"
                raise ValueError(msg)

        if widget_settings is not None:
            invalid_settings = set(widget_settings.keys()) - set(
                AVAILABLE_WIDGETS.keys(),
            )
            if invalid_settings:
                msg = f"Widget settings reference invalid widgets: {invalid_settings}"
                raise ValueError(msg)

        # Get or create settings
        settings = await self._settings_repo.get_or_create()

        # Apply updates
        settings.update_sync(
            auto_post_transactions=auto_post_transactions,
            default_currency=default_currency,
        )
        settings.update_display(
            show_draft_transactions=show_draft_transactions,
            default_date_range_days=default_date_range_days,
        )
        settings.update_dashboard(
            enabled_widgets=enabled_widgets,
            widget_settings=widget_settings,
        )
        settings.update_ai(
            enabled=ai_enabled,
            model_name=ai_model_name,
            min_confidence=ai_min_confidence,
        )

        await self._settings_repo.save(settings)
        return settings
