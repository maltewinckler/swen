"""SQLAlchemy implementation of UserSettingsRepository."""

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.settings import (
    AISettings,
    DashboardSettings,
    DisplaySettings,
    SyncSettings,
    UserSettings,
    UserSettingsRepository,
)
from swen.infrastructure.persistence.sqlalchemy.models.settings import (
    UserSettingsModel,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser


class UserSettingsRepositorySQLAlchemy(UserSettingsRepository):
    """SQLAlchemy implementation of UserSettingsRepository.

    This repository is user-scoped - all operations automatically apply to
    the current user passed at construction time.
    """

    def __init__(self, session: AsyncSession, current_user: "CurrentUser") -> None:
        self._session = session
        self._current_user = current_user

    async def get_or_create(self) -> UserSettings:
        """Get user settings, creating defaults if not exists."""
        settings = await self.find()
        if settings is not None:
            return settings

        # Create default settings
        settings = UserSettings.default(self._current_user.user_id)
        await self.save(settings)
        return settings

    async def find(self) -> UserSettings | None:
        """Find settings for current user, returns None if not exists."""
        stmt = select(UserSettingsModel).where(
            UserSettingsModel.user_id == self._current_user.user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._map_to_domain(model)

    async def save(self, settings: UserSettings) -> None:
        """Save user settings."""
        # Check if exists
        stmt = select(UserSettingsModel).where(
            UserSettingsModel.user_id == settings.user_id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Update existing
            self._update_model(existing, settings)
        else:
            # Create new
            model = self._map_to_model(settings)
            self._session.add(model)

        await self._session.flush()

    async def delete(self) -> bool:
        """Delete user settings. Returns True if deleted."""
        # Find existing model first
        stmt = select(UserSettingsModel).where(
            UserSettingsModel.user_id == self._current_user.user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    def _map_to_domain(self, model: UserSettingsModel) -> UserSettings:
        """Map SQLAlchemy model to domain aggregate."""
        # Handle dashboard widgets - could be None or list
        enabled_widgets = model.dashboard_enabled_widgets
        if enabled_widgets is None:
            enabled_widgets = list(DashboardSettings().enabled_widgets)

        return UserSettings(
            user_id=model.user_id,
            sync=SyncSettings(
                auto_post_transactions=model.auto_post_transactions,
                default_currency=model.default_currency,
            ),
            display=DisplaySettings(
                show_draft_transactions=model.show_draft_transactions,
                default_date_range_days=model.default_date_range_days,
            ),
            dashboard=DashboardSettings(
                enabled_widgets=tuple(enabled_widgets),
                widget_settings=model.dashboard_widget_settings or {},
            ),
            ai=AISettings(
                enabled=model.ai_enabled,
                model_name=model.ai_model_name,
                min_confidence=model.ai_min_confidence,
            ),
        )

    def _map_to_model(self, settings: UserSettings) -> UserSettingsModel:
        """Map domain aggregate to SQLAlchemy model."""
        return UserSettingsModel(
            user_id=settings.user_id,
            auto_post_transactions=settings.sync.auto_post_transactions,
            default_currency=settings.sync.default_currency,
            show_draft_transactions=settings.display.show_draft_transactions,
            default_date_range_days=settings.display.default_date_range_days,
            dashboard_enabled_widgets=list(settings.dashboard.enabled_widgets),
            dashboard_widget_settings=settings.dashboard.widget_settings,
            ai_enabled=settings.ai.enabled,
            ai_model_name=settings.ai.model_name,
            ai_min_confidence=settings.ai.min_confidence,
        )

    def _update_model(
        self,
        model: UserSettingsModel,
        settings: UserSettings,
    ) -> None:
        """Update model from domain aggregate."""
        model.auto_post_transactions = settings.sync.auto_post_transactions
        model.default_currency = settings.sync.default_currency
        model.show_draft_transactions = settings.display.show_draft_transactions
        model.default_date_range_days = settings.display.default_date_range_days
        model.dashboard_enabled_widgets = list(settings.dashboard.enabled_widgets)
        model.dashboard_widget_settings = settings.dashboard.widget_settings
        model.ai_enabled = settings.ai.enabled
        model.ai_model_name = settings.ai.model_name
        model.ai_min_confidence = settings.ai.min_confidence
