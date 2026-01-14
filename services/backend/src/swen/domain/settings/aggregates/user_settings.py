"""UserSettings aggregate for application preferences for a user."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from swen.domain.settings.value_objects import (
    AISettings,
    DashboardSettings,
    DisplaySettings,
    SyncSettings,
)


@dataclass
class UserSettings:
    """User application settings aggregate.

    This aggregate is keyed by user_id (not a generated ID).
    It represents the consistency boundary for all user preferences.
    """

    user_id: UUID
    sync: SyncSettings = field(default_factory=SyncSettings.default)
    display: DisplaySettings = field(default_factory=DisplaySettings.default)
    dashboard: DashboardSettings = field(default_factory=DashboardSettings.default)
    ai: AISettings = field(default_factory=AISettings.default)

    @classmethod
    def default(cls, user_id: UUID) -> "UserSettings":
        """Create default settings for a user."""
        return cls(
            user_id=user_id,
            sync=SyncSettings.default(),
            display=DisplaySettings.default(),
            dashboard=DashboardSettings.default(),
            ai=AISettings.default(),
        )

    def update_sync(
        self,
        auto_post_transactions: bool | None = None,
        default_currency: str | None = None,
    ) -> None:
        """Update sync settings."""
        if auto_post_transactions is not None:
            self.sync = self.sync.with_auto_post(auto_post_transactions)
        if default_currency is not None:
            self.sync = self.sync.with_currency(default_currency)

    def update_display(
        self,
        show_draft_transactions: bool | None = None,
        default_date_range_days: int | None = None,
    ) -> None:
        """Update display settings."""
        if show_draft_transactions is not None:
            self.display = self.display.with_show_drafts(show_draft_transactions)
        if default_date_range_days is not None:
            self.display = self.display.with_date_range(default_date_range_days)

    def update_dashboard(
        self,
        enabled_widgets: list[str] | None = None,
        widget_settings: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Update dashboard settings."""
        if enabled_widgets is not None:
            self.dashboard = self.dashboard.with_enabled_widgets(enabled_widgets)
        if widget_settings is not None:
            self.dashboard = self.dashboard.with_all_widget_settings(widget_settings)

    def update_ai(
        self,
        enabled: bool | None = None,
        model_name: str | None = None,
        min_confidence: float | None = None,
    ) -> None:
        """Update AI settings."""
        if enabled is not None:
            self.ai = self.ai.with_enabled(enabled)
        if model_name is not None:
            self.ai = self.ai.with_model(model_name)
        if min_confidence is not None:
            self.ai = self.ai.with_confidence(min_confidence)

    def reset(self) -> None:
        """Reset all settings to defaults."""
        self.sync = SyncSettings.default()
        self.display = DisplaySettings.default()
        self.dashboard = DashboardSettings.default()
        self.ai = AISettings.default()
