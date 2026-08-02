"""Preferences router for user settings management."""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import ConfigDict

from swen.application.settings.commands import (
    ResetUserSettingsCommand,
    UpdateUserSettingsCommand,
)
from swen.application.settings.dtos import (
    AvailableWidgetsDTO,
    DashboardSettingsDTO,
    UserSettingsDTO,
    UserSettingsUpdateDTO,
)
from swen.application.settings.queries import (
    GetAvailableWidgetsQuery,
    GetUserSettingsQuery,
)
from swen.presentation.api.dependencies import RepoFactoryDep

logger = logging.getLogger(__name__)

router = APIRouter()


# returned standalone from /dashboard, /dashboard/reset, and PATCH /dashboard,
# so it earns its own Response class (unlike sync/display/ai settings below).
class DashboardSettingsResponse(DashboardSettingsDTO):
    """Dashboard widget configuration."""

    model_config = ConfigDict(from_attributes=True)


class UserSettingsResponse(UserSettingsDTO):
    """Full user settings response.

    sync_settings/display_settings/ai_settings are never returned standalone,
    so they inherit their DTO types directly (SyncSettingsDTO etc.) rather
    than going through a dedicated Response subclass -- only dashboard_settings
    has one, since that's also returned standalone below.
    """

    dashboard_settings: DashboardSettingsResponse

    model_config = ConfigDict(
        from_attributes=True,
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


class UserSettingsUpdateRequest(UserSettingsUpdateDTO):
    """Request to update user preferences."""


class AvailableWidgetsResponse(AvailableWidgetsDTO):
    """List of all available widgets with their metadata."""

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "",
    summary="Get user preferences",
    responses={
        200: {"description": "Current user preferences"},
    },
)
async def get_preferences(
    factory: RepoFactoryDep,
) -> UserSettingsResponse:
    """
    Get the current user's preferences.

    Returns sync, display, dashboard, and AI settings.
    """
    query = GetUserSettingsQuery.from_factory(factory)
    preferences = await query.execute()
    return UserSettingsResponse.model_validate(preferences)


@router.patch(
    "",
    summary="Update user preferences",
    responses={
        200: {"description": "Updated preferences"},
        400: {"description": "Invalid preference values"},
    },
)
async def update_preferences(
    request: UserSettingsUpdateRequest,
    factory: RepoFactoryDep,
) -> UserSettingsResponse:
    """
    Update user preferences.

    Only provided fields will be updated; others remain unchanged.
    """
    command = UpdateUserSettingsCommand.from_factory(factory)

    try:
        preferences = await command.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info("User preferences updated")
    return UserSettingsResponse.model_validate(preferences)


@router.post(
    "/reset",
    summary="Reset preferences to defaults",
    responses={
        200: {"description": "Preferences reset to defaults"},
    },
)
async def reset_preferences(
    factory: RepoFactoryDep,
) -> UserSettingsResponse:
    """Reset all user preferences to default values."""
    command = ResetUserSettingsCommand.from_factory(factory)
    preferences = await command.execute()

    logger.info("User preferences reset to defaults")
    return UserSettingsResponse.model_validate(preferences)


@router.get(
    "/dashboard",
    summary="Get dashboard settings",
    responses={
        200: {"description": "Current dashboard widget configuration"},
    },
)
async def get_dashboard_settings(
    factory: RepoFactoryDep,
) -> DashboardSettingsResponse:
    """Get the current user's dashboard widget configuration."""
    query = GetUserSettingsQuery.from_factory(factory)
    preferences = await query.execute()
    return DashboardSettingsResponse.model_validate(preferences.dashboard_settings)


@router.patch(
    "/dashboard",
    summary="Update dashboard settings",
    responses={
        200: {"description": "Updated dashboard settings"},
        400: {"description": "Invalid widget IDs"},
    },
)
async def update_dashboard_settings(
    request: UserSettingsUpdateRequest,
    factory: RepoFactoryDep,
) -> DashboardSettingsResponse:
    """Update dashboard widget configuration."""
    if request.enabled_widgets is None and request.widget_settings is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least enabled_widgets or widget_settings must be provided",
        )

    command = UpdateUserSettingsCommand.from_factory(factory)

    try:
        preferences = await command.execute(
            UserSettingsUpdateDTO(
                enabled_widgets=request.enabled_widgets,
                widget_settings=request.widget_settings,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info("Dashboard settings updated")
    return DashboardSettingsResponse.model_validate(preferences.dashboard_settings)


@router.post(
    "/dashboard/reset",
    summary="Reset dashboard to defaults",
    responses={
        200: {"description": "Dashboard reset to default widgets"},
    },
)
async def reset_dashboard_settings(
    factory: RepoFactoryDep,
) -> DashboardSettingsResponse:
    """Reset dashboard to default widget configuration."""
    # Reset all settings, then return just dashboard
    command = ResetUserSettingsCommand.from_factory(factory)
    preferences = await command.execute()

    logger.info("Dashboard settings reset to defaults")
    return DashboardSettingsResponse.model_validate(preferences.dashboard_settings)


@router.get(
    "/dashboard/widgets",
    summary="List available widgets",
    responses={
        200: {"description": "All available widgets with metadata"},
    },
)
async def list_available_widgets(
    factory: RepoFactoryDep,
) -> AvailableWidgetsResponse:
    """Get all available dashboard widgets with their metadata."""
    query = GetAvailableWidgetsQuery.from_factory(factory)
    widgets = await query.execute()
    return AvailableWidgetsResponse.model_validate(widgets)
