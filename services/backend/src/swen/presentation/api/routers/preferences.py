"""Preferences router for user preference management."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from swen.application.commands.user import (
    ResetDashboardSettingsCommand,
    ResetUserPreferencesCommand,
    UpdateDashboardSettingsCommand,
    UpdateUserPreferencesCommand,
)
from swen.domain.user import AVAILABLE_WIDGETS, DEFAULT_ENABLED_WIDGETS
from swen.presentation.api.dependencies import RepoFactory
from pydantic import BaseModel, Field

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

class PreferencesResponse(BaseModel):
    """Full user preferences response."""

    sync_settings: SyncSettingsResponse
    display_settings: DisplaySettingsResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "sync_settings": {
                    "auto_post_transactions": False,
                    "default_currency": "EUR",
                },
                "display_settings": {
                    "show_draft_transactions": True,
                    "default_date_range_days": 30,
                },
            },
        },
    }

class PreferencesUpdateRequest(BaseModel):
    """Request to update user preferences.

    All fields are optional - only provided fields will be updated.
    """

    auto_post_transactions: Optional[bool] = Field(
        None,
        description="Automatically post imported transactions",
    )
    default_currency: Optional[str] = Field(
        None,
        description="Default currency code (e.g., EUR, USD)",
    )
    show_draft_transactions: Optional[bool] = Field(
        None,
        description="Show draft transactions in lists",
    )
    default_date_range_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Default date range for filters (1-365)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "auto_post_transactions": True,
                "default_currency": "EUR",
                "show_draft_transactions": False,
                "default_date_range_days": 90,
            },
        },
    }

class WidgetInfoResponse(BaseModel):
    """Information about an available widget."""

    id: str = Field(description="Widget ID")
    title: str = Field(description="Display title")
    description: str = Field(description="Brief description")
    category: str = Field(description="Widget category (overview, spending, income)")
    enabled: bool = Field(description="Whether the widget is currently enabled")
    settings: dict[str, Any] = Field(description="Current settings for this widget")

class DashboardSettingsResponse(BaseModel):
    """Dashboard widget configuration."""

    enabled_widgets: list[str] = Field(
        description="List of enabled widget IDs in display order"
    )
    widget_settings: dict[str, dict[str, Any]] = Field(
        description="Per-widget settings"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled_widgets": ["summary-cards", "spending-pie", "account-balances"],
                "widget_settings": {
                    "spending-pie": {"months": 3},
                    "net-worth": {"months": 12},
                },
            },
        },
    }

class DashboardSettingsUpdateRequest(BaseModel):
    """Request to update dashboard settings.

    Both fields are optional - only provided fields will be updated.
    """

    enabled_widgets: Optional[list[str]] = Field(
        None,
        description="List of widget IDs in display order",
    )
    widget_settings: Optional[dict[str, dict[str, Any]]] = Field(
        None,
        description="Per-widget settings (e.g., time ranges)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled_widgets": [
                    "summary-cards",
                    "net-worth",
                    "spending-pie",
                    "income-over-time",
                ],
                "widget_settings": {
                    "net-worth": {"months": 24},
                    "spending-pie": {"months": 3},
                },
            },
        },
    }

class AvailableWidgetsResponse(BaseModel):
    """List of all available widgets with their metadata."""

    widgets: list[WidgetInfoResponse] = Field(description="All available widgets")
    default_widgets: list[str] = Field(
        description="Default enabled widgets for new users"
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

    Returns both sync settings and display settings.
    """
    user_repo = factory.user_repository()
    user = await user_repo.get_or_create_by_email(factory.user_context.email)

    prefs = user.preferences

    return PreferencesResponse(
        sync_settings=SyncSettingsResponse(
            auto_post_transactions=prefs.sync_settings.auto_post_transactions,
            default_currency=prefs.sync_settings.default_currency,
        ),
        display_settings=DisplaySettingsResponse(
            show_draft_transactions=prefs.display_settings.show_draft_transactions,
            default_date_range_days=prefs.display_settings.default_date_range_days,
        ),
    )

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

    **Example:** Update only auto-post setting:
    ```json
    {"auto_post_transactions": true}
    ```
    """
    # Check if any update is provided
    if all(
        v is None
        for v in [
            request.auto_post_transactions,
            request.default_currency,
            request.show_draft_transactions,
            request.default_date_range_days,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one preference must be provided",
        )

    command = UpdateUserPreferencesCommand.from_factory(factory)

    try:
        user = await command.execute(
            auto_post_transactions=request.auto_post_transactions,
            default_currency=request.default_currency,
            show_draft_transactions=request.show_draft_transactions,
            default_date_range_days=request.default_date_range_days,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("User preferences updated")

    prefs = user.preferences
    return PreferencesResponse(
        sync_settings=SyncSettingsResponse(
            auto_post_transactions=prefs.sync_settings.auto_post_transactions,
            default_currency=prefs.sync_settings.default_currency,
        ),
        display_settings=DisplaySettingsResponse(
            show_draft_transactions=prefs.display_settings.show_draft_transactions,
            default_date_range_days=prefs.display_settings.default_date_range_days,
        ),
    )

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
    """
    Reset all user preferences to default values.

    **Default values:**
    - `auto_post_transactions`: false
    - `default_currency`: EUR
    - `show_draft_transactions`: true
    - `default_date_range_days`: 30
    """
    command = ResetUserPreferencesCommand.from_factory(factory)
    user = await command.execute()
    await factory.session.commit()

    logger.info("User preferences reset to defaults")

    prefs = user.preferences
    return PreferencesResponse(
        sync_settings=SyncSettingsResponse(
            auto_post_transactions=prefs.sync_settings.auto_post_transactions,
            default_currency=prefs.sync_settings.default_currency,
        ),
        display_settings=DisplaySettingsResponse(
            show_draft_transactions=prefs.display_settings.show_draft_transactions,
            default_date_range_days=prefs.display_settings.default_date_range_days,
        ),
    )

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
    """
    Get the current user's dashboard widget configuration.

    Returns the list of enabled widgets (in display order) and
    per-widget settings.
    """
    user_repo = factory.user_repository()
    user = await user_repo.get_or_create_by_email(factory.user_context.email)

    dashboard = user.preferences.dashboard_settings

    return DashboardSettingsResponse(
        enabled_widgets=list(dashboard.enabled_widgets),
        widget_settings=dashboard.widget_settings,
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
    request: DashboardSettingsUpdateRequest,
    factory: RepoFactory,
) -> DashboardSettingsResponse:
    """
    Update dashboard widget configuration.

    Only provided fields will be updated; others remain unchanged.

    **Example:** Enable specific widgets in order:
    ```json
    {
        "enabled_widgets": ["summary-cards", "net-worth", "spending-pie"]
    }
    ```

    **Example:** Update settings for a widget:
    ```json
    {
        "widget_settings": {
            "net-worth": {"months": 24}
        }
    }
    ```
    """
    # Check if any update is provided
    if request.enabled_widgets is None and request.widget_settings is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least enabled_widgets or widget_settings must be provided",
        )

    command = UpdateDashboardSettingsCommand.from_factory(factory)

    try:
        user = await command.execute(
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

    dashboard = user.preferences.dashboard_settings
    return DashboardSettingsResponse(
        enabled_widgets=list(dashboard.enabled_widgets),
        widget_settings=dashboard.widget_settings,
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
    """
    Reset dashboard to default widget configuration.

    **Default widgets:**
    - summary-cards
    - spending-pie
    - account-balances

    Other preferences (sync, display) are preserved.
    """
    command = ResetDashboardSettingsCommand.from_factory(factory)
    user = await command.execute()
    await factory.session.commit()

    logger.info("Dashboard settings reset to defaults")

    dashboard = user.preferences.dashboard_settings
    return DashboardSettingsResponse(
        enabled_widgets=list(dashboard.enabled_widgets),
        widget_settings=dashboard.widget_settings,
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
    """
    Get all available dashboard widgets with their metadata.

    Returns widget info including:
    - ID, title, description, category
    - Whether each widget is currently enabled
    - Current settings for each widget (with defaults applied)

    Useful for building a widget configuration UI.
    """
    user_repo = factory.user_repository()
    user = await user_repo.get_or_create_by_email(factory.user_context.email)

    dashboard = user.preferences.dashboard_settings

    widgets = []
    for widget_id, widget_meta in AVAILABLE_WIDGETS.items():
        widgets.append(
            WidgetInfoResponse(
                id=widget_id,
                title=widget_meta["title"],
                description=widget_meta["description"],
                category=widget_meta["category"],
                enabled=dashboard.is_widget_enabled(widget_id),
                settings=dashboard.get_widget_settings(widget_id),
            )
        )

    return AvailableWidgetsResponse(
        widgets=widgets,
        default_widgets=list(DEFAULT_ENABLED_WIDGETS),
    )
