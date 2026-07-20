"""DTOs for user settings (preferences) queries and commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from swen.domain.settings import AVAILABLE_WIDGETS, DEFAULT_ENABLED_WIDGETS

if TYPE_CHECKING:
    from swen.domain.settings import UserSettings


class SyncSettingsDTO(BaseModel):
    """Sync-related settings."""

    model_config = ConfigDict(frozen=True)

    auto_post_transactions: bool
    default_currency: str


class DisplaySettingsDTO(BaseModel):
    """Display-related settings."""

    model_config = ConfigDict(frozen=True)

    show_draft_transactions: bool
    default_date_range_days: int


class AISettingsDTO(BaseModel):
    """AI-related settings."""

    # protected_namespaces=() so `model_name` doesn't clash with pydantic's `model_*`.
    model_config = ConfigDict(frozen=True, protected_namespaces=())

    enabled: bool
    model_name: str
    min_confidence: float


class DashboardSettingsDTO(BaseModel):
    """Dashboard widget configuration."""

    model_config = ConfigDict(frozen=True)

    enabled_widgets: list[str]
    widget_settings: dict[str, dict[str, Any]]


class UserSettingsDTO(BaseModel):
    """Full user settings."""

    model_config = ConfigDict(frozen=True)

    sync_settings: SyncSettingsDTO
    display_settings: DisplaySettingsDTO
    dashboard_settings: DashboardSettingsDTO
    ai_settings: AISettingsDTO

    @classmethod
    def from_user_settings(cls, settings: UserSettings) -> UserSettingsDTO:
        return cls(
            sync_settings=SyncSettingsDTO(
                auto_post_transactions=settings.sync.auto_post_transactions,
                default_currency=settings.sync.default_currency,
            ),
            display_settings=DisplaySettingsDTO(
                show_draft_transactions=settings.display.show_draft_transactions,
                default_date_range_days=settings.display.default_date_range_days,
            ),
            dashboard_settings=DashboardSettingsDTO(
                enabled_widgets=list(settings.dashboard.enabled_widgets),
                widget_settings=settings.dashboard.widget_settings,
            ),
            ai_settings=AISettingsDTO(
                enabled=settings.ai.enabled,
                model_name=settings.ai.model_name,
                min_confidence=settings.ai.min_confidence,
            ),
        )


class UserSettingsUpdateDTO(BaseModel):
    """Partial update for user settings. All fields optional."""

    # Sync settings
    auto_post_transactions: bool | None = None
    default_currency: str | None = None
    # Display settings
    show_draft_transactions: bool | None = None
    default_date_range_days: int | None = Field(default=None, ge=1, le=365)
    # Dashboard settings
    enabled_widgets: list[str] | None = None
    widget_settings: dict[str, dict[str, Any]] | None = None
    # AI settings
    ai_enabled: bool | None = None
    ai_model_name: str | None = None
    ai_min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    def is_empty(self) -> bool:
        """True if no field was provided (nothing to update)."""
        return all(value is None for value in self.__dict__.values())


class WidgetInfoDTO(BaseModel):
    """Metadata and current state for a single available dashboard widget."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    description: str
    category: str
    enabled: bool
    settings: dict[str, Any]


class AvailableWidgetsDTO(BaseModel):
    """Catalog of all available dashboard widgets with their current state."""

    model_config = ConfigDict(frozen=True)

    widgets: list[WidgetInfoDTO]
    default_widgets: list[str]

    @classmethod
    def from_user_settings(cls, settings: UserSettings) -> AvailableWidgetsDTO:
        widgets = [
            WidgetInfoDTO(
                id=widget_id,
                title=meta["title"],
                description=meta["description"],
                category=meta["category"],
                enabled=settings.dashboard.is_widget_enabled(widget_id),
                settings=settings.dashboard.get_widget_settings(widget_id),
            )
            for widget_id, meta in AVAILABLE_WIDGETS.items()
        ]
        return cls(
            widgets=widgets,
            default_widgets=list(DEFAULT_ENABLED_WIDGETS),
        )
