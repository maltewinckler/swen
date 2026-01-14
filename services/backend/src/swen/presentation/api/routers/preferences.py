"""Preferences router for user settings management."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from swen.application.commands.settings import (
    ResetUserSettingsCommand,
    UpdateUserSettingsCommand,
)
from swen.application.queries.settings import GetUserSettingsQuery
from swen.domain.settings import AVAILABLE_WIDGETS, DEFAULT_ENABLED_WIDGETS
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()


class SyncSettingsResponse(BaseModel):
    """Sync-related preferences."""

    auto_post_transactions: bool = Field(
        description="Automatically post (finalize) imported transactions",
    )
    default_currency: str = Field(description="Default currency code (e.g., EUR)")


class DisplaySettingsResponse(BaseModel):
    """Display-related preferences."""

    show_draft_transactions: bool = Field(
        description="Show draft transactions in lists/exports",
    )
    default_date_range_days: int = Field(description="Default days for date filters")


class AISettingsResponse(BaseModel):
    """AI-related preferences."""

    enabled: bool = Field(description="Whether AI categorization is enabled")
    model_name: str = Field(description="AI model name")
    min_confidence: float = Field(description="Minimum confidence threshold")


class DashboardSettingsResponse(BaseModel):
    """Dashboard widget configuration."""

    enabled_widgets: list[str] = Field(
        description="List of enabled widget IDs in display order",
    )
    widget_settings: dict[str, dict[str, Any]] = Field(
        description="Per-widget settings",
    )


class PreferencesResponse(BaseModel):
    """Full user preferences response."""

    sync_settings: SyncSettingsResponse
    display_settings: DisplaySettingsResponse
    dashboard_settings: DashboardSettingsResponse
    ai_settings: AISettingsResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sync_settings": {
                    "auto_post_transactions": False,
                    "default_currency": "EUR",
                },
                "display_settings": {
                    "show_draft_transactions": True,
                    "default_date_range_days": 30,
                },
                "dashboard_settings": {
                    "enabled_widgets": [
                        "summary-cards",
                        "spending-pie",
                        "account-balances",
                    ],
                    "widget_settings": {},
                },
                "ai_settings": {
                    "enabled": True,
                    "model_name": "qwen2.5:3b",
                    "min_confidence": 0.7,
                },
            },
        },
    )


class PreferencesUpdateRequest(BaseModel):
    """Request to update user preferences.

    All fields are optional - only provided fields will be updated.
    """

    # Sync settings
    auto_post_transactions: bool | None = Field(
        None,
        description="Automatically post imported transactions",
    )
    default_currency: str | None = Field(
        None,
        description="Default currency code (e.g., EUR, USD)",
    )
    # Display settings
    show_draft_transactions: bool | None = Field(
        None,
        description="Show draft transactions in lists",
    )
    default_date_range_days: int | None = Field(
        None,
        ge=1,
        le=365,
        description="Default date range for filters (1-365)",
    )
    # Dashboard settings
    enabled_widgets: list[str] | None = Field(
        None,
        description="List of widget IDs in display order",
    )
    widget_settings: dict[str, dict[str, Any]] | None = Field(
        None,
        description="Per-widget settings",
    )
    # AI settings
    ai_enabled: bool | None = Field(
        None,
        description="Enable AI categorization",
    )
    ai_model_name: str | None = Field(
        None,
        description="AI model name",
    )
    ai_min_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold (0-1)",
    )


class WidgetInfoResponse(BaseModel):
    """Information about an available widget."""

    id: str = Field(description="Widget ID")
    title: str = Field(description="Display title")
    description: str = Field(description="Brief description")
    category: str = Field(description="Widget category (overview, spending, income)")
    enabled: bool = Field(description="Whether the widget is currently enabled")
    settings: dict[str, Any] = Field(description="Current settings for this widget")


class AvailableWidgetsResponse(BaseModel):
    """List of all available widgets with their metadata."""

    widgets: list[WidgetInfoResponse] = Field(description="All available widgets")
    default_widgets: list[str] = Field(
        description="Default enabled widgets for new users",
    )


def _settings_to_response(settings: Any) -> PreferencesResponse:
    """Convert UserSettings to API response."""
    return PreferencesResponse(
        sync_settings=SyncSettingsResponse(
            auto_post_transactions=settings.sync.auto_post_transactions,
            default_currency=settings.sync.default_currency,
        ),
        display_settings=DisplaySettingsResponse(
            show_draft_transactions=settings.display.show_draft_transactions,
            default_date_range_days=settings.display.default_date_range_days,
        ),
        dashboard_settings=DashboardSettingsResponse(
            enabled_widgets=list(settings.dashboard.enabled_widgets),
            widget_settings=settings.dashboard.widget_settings,
        ),
        ai_settings=AISettingsResponse(
            enabled=settings.ai.enabled,
            model_name=settings.ai.model_name,
            min_confidence=settings.ai.min_confidence,
        ),
    )


@router.get(
    "",
    summary="Get user preferences",
    responses={
        200: {"description": "Current user preferences"},
    },
)
async def get_preferences(
    factory: RepoFactory,
) -> PreferencesResponse:
    """
    Get the current user's preferences.

    Returns sync, display, dashboard, and AI settings.
    """
    query = GetUserSettingsQuery.from_factory(factory)
    settings = await query.execute()
    return _settings_to_response(settings)


@router.patch(
    "",
    summary="Update user preferences",
    responses={
        200: {"description": "Updated preferences"},
        400: {"description": "Invalid preference values"},
    },
)
async def update_preferences(
    request: PreferencesUpdateRequest,
    factory: RepoFactory,
) -> PreferencesResponse:
    """
    Update user preferences.

    Only provided fields will be updated; others remain unchanged.
    """
    # Check if any update is provided
    if all(
        v is None
        for v in [
            request.auto_post_transactions,
            request.default_currency,
            request.show_draft_transactions,
            request.default_date_range_days,
            request.enabled_widgets,
            request.widget_settings,
            request.ai_enabled,
            request.ai_model_name,
            request.ai_min_confidence,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one preference must be provided",
        )

    command = UpdateUserSettingsCommand.from_factory(factory)

    try:
        settings = await command.execute(
            auto_post_transactions=request.auto_post_transactions,
            default_currency=request.default_currency,
            show_draft_transactions=request.show_draft_transactions,
            default_date_range_days=request.default_date_range_days,
            enabled_widgets=request.enabled_widgets,
            widget_settings=request.widget_settings,
            ai_enabled=request.ai_enabled,
            ai_model_name=request.ai_model_name,
            ai_min_confidence=request.ai_min_confidence,
        )
        await factory.session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception:
        await factory.session.rollback()
        raise

    logger.info("User preferences updated")
    return _settings_to_response(settings)


@router.post(
    "/reset",
    summary="Reset preferences to defaults",
    responses={
        200: {"description": "Preferences reset to defaults"},
    },
)
async def reset_preferences(
    factory: RepoFactory,
) -> PreferencesResponse:
    """Reset all user preferences to default values."""
    command = ResetUserSettingsCommand.from_factory(factory)
    settings = await command.execute()
    await factory.session.commit()

    logger.info("User preferences reset to defaults")
    return _settings_to_response(settings)


@router.get(
    "/dashboard",
    summary="Get dashboard settings",
    responses={
        200: {"description": "Current dashboard widget configuration"},
    },
)
async def get_dashboard_settings(
    factory: RepoFactory,
) -> DashboardSettingsResponse:
    """Get the current user's dashboard widget configuration."""
    query = GetUserSettingsQuery.from_factory(factory)
    settings = await query.execute()

    return DashboardSettingsResponse(
        enabled_widgets=list(settings.dashboard.enabled_widgets),
        widget_settings=settings.dashboard.widget_settings,
    )


@router.patch(
    "/dashboard",
    summary="Update dashboard settings",
    responses={
        200: {"description": "Updated dashboard settings"},
        400: {"description": "Invalid widget IDs"},
    },
)
async def update_dashboard_settings(
    request: PreferencesUpdateRequest,
    factory: RepoFactory,
) -> DashboardSettingsResponse:
    """Update dashboard widget configuration."""
    if request.enabled_widgets is None and request.widget_settings is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least enabled_widgets or widget_settings must be provided",
        )

    command = UpdateUserSettingsCommand.from_factory(factory)

    try:
        settings = await command.execute(
            enabled_widgets=request.enabled_widgets,
            widget_settings=request.widget_settings,
        )
        await factory.session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception:
        await factory.session.rollback()
        raise

    logger.info("Dashboard settings updated")
    return DashboardSettingsResponse(
        enabled_widgets=list(settings.dashboard.enabled_widgets),
        widget_settings=settings.dashboard.widget_settings,
    )


@router.post(
    "/dashboard/reset",
    summary="Reset dashboard to defaults",
    responses={
        200: {"description": "Dashboard reset to default widgets"},
    },
)
async def reset_dashboard_settings(
    factory: RepoFactory,
) -> DashboardSettingsResponse:
    """Reset dashboard to default widget configuration."""
    # Reset all settings, then return just dashboard
    command = ResetUserSettingsCommand.from_factory(factory)
    settings = await command.execute()
    await factory.session.commit()

    logger.info("Dashboard settings reset to defaults")
    return DashboardSettingsResponse(
        enabled_widgets=list(settings.dashboard.enabled_widgets),
        widget_settings=settings.dashboard.widget_settings,
    )


@router.get(
    "/dashboard/widgets",
    summary="List available widgets",
    responses={
        200: {"description": "All available widgets with metadata"},
    },
)
async def list_available_widgets(
    factory: RepoFactory,
) -> AvailableWidgetsResponse:
    """Get all available dashboard widgets with their metadata."""
    query = GetUserSettingsQuery.from_factory(factory)
    settings = await query.execute()

    widgets = []
    for widget_id, widget_meta in AVAILABLE_WIDGETS.items():
        widgets.append(
            WidgetInfoResponse(
                id=widget_id,
                title=widget_meta["title"],
                description=widget_meta["description"],
                category=widget_meta["category"],
                enabled=settings.dashboard.is_widget_enabled(widget_id),
                settings=settings.dashboard.get_widget_settings(widget_id),
            ),
        )

    return AvailableWidgetsResponse(
        widgets=widgets,
        default_widgets=list(DEFAULT_ENABLED_WIDGETS),
    )
