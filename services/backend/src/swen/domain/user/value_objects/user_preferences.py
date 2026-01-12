"""User preferences value object.

Combines all preference categories into a single immutable value object.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from swen.domain.user.value_objects.ai_settings import AISettings
from swen.domain.user.value_objects.dashboard_settings import DashboardSettings
from swen.domain.user.value_objects.display_settings import DisplaySettings
from swen.domain.user.value_objects.sync_settings import SyncSettings


@dataclass(frozen=True)
class UserPreferences:
    """Complete user preferences combining all settings categories."""

    sync_settings: SyncSettings = field(default_factory=SyncSettings)
    display_settings: DisplaySettings = field(default_factory=DisplaySettings)
    dashboard_settings: DashboardSettings = field(default_factory=DashboardSettings)
    ai_settings: AISettings = field(default_factory=AISettings)

    def with_updates(
        self,
        auto_post_transactions: Optional[bool] = None,
        default_currency: Optional[str] = None,
        show_draft_transactions: Optional[bool] = None,
        default_date_range_days: Optional[int] = None,
    ) -> "UserPreferences":
        new_sync = self.sync_settings
        if auto_post_transactions is not None:
            new_sync = new_sync.with_auto_post(auto_post_transactions)
        if default_currency is not None:
            new_sync = new_sync.with_currency(default_currency)

        # Update display settings
        new_display = self.display_settings
        if show_draft_transactions is not None:
            new_display = new_display.with_show_drafts(show_draft_transactions)
        if default_date_range_days is not None:
            new_display = new_display.with_date_range(default_date_range_days)

        return UserPreferences(
            sync_settings=new_sync,
            display_settings=new_display,
            dashboard_settings=self.dashboard_settings,
            ai_settings=self.ai_settings,
        )

    def with_dashboard_updates(
        self,
        enabled_widgets: Optional[list[str]] = None,
        widget_settings: Optional[dict[str, dict[str, Any]]] = None,
    ) -> "UserPreferences":
        new_dashboard = self.dashboard_settings

        if enabled_widgets is not None:
            new_dashboard = new_dashboard.with_enabled_widgets(enabled_widgets)

        if widget_settings is not None:
            new_dashboard = new_dashboard.with_all_widget_settings(widget_settings)

        return UserPreferences(
            sync_settings=self.sync_settings,
            display_settings=self.display_settings,
            dashboard_settings=new_dashboard,
            ai_settings=self.ai_settings,
        )

    def with_ai_updates(
        self,
        enabled: Optional[bool] = None,
        model_name: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> "UserPreferences":
        new_ai = self.ai_settings

        if enabled is not None:
            new_ai = new_ai.with_enabled(enabled)

        if model_name is not None:
            new_ai = new_ai.with_model(model_name)

        if min_confidence is not None:
            new_ai = new_ai.with_confidence(min_confidence)

        return UserPreferences(
            sync_settings=self.sync_settings,
            display_settings=self.display_settings,
            dashboard_settings=self.dashboard_settings,
            ai_settings=new_ai,
        )
