"""Admin FinTS provider management endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.commands.system import (
    ActivateFintsProviderCommand,
    FintsProviderMode,
    GeldstromApiVerificationError,
    ProviderNotConfiguredError,
    SaveGeldstromApiConfigCommand,
)
from swen.application.queries.system import (
    GetFintsProviderStatusQuery,
    GetGeldstromApiConfigQuery,
)
from swen.presentation.api.dependencies import (
    AdminUser,
    DBSession,
    RepoFactory,
)
from swen.presentation.api.schemas.fints_provider import (
    ActivateProviderRequest,
    FintsProviderStatusResponse,
    GeldstromApiConfigResponse,
    SaveGeldstromApiConfigRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fints_provider", tags=["admin-fints-provider"])


@router.get(
    "/status",
    summary="Get FinTS provider status",
    responses={
        200: {"description": "Provider status"},
        403: {"description": "Admin access required"},
    },
)
async def get_provider_status(
    _admin: AdminUser,
    factory: RepoFactory,
) -> FintsProviderStatusResponse:
    """Get which FinTS provider is active and configured."""
    query = GetFintsProviderStatusQuery.from_factory(factory)
    result = await query.execute()

    return FintsProviderStatusResponse(
        local_configured=result.local_configured,
        local_active=result.local_active,
        api_configured=result.api_configured,
        api_active=result.api_active,
        active_provider=result.active_provider,
    )


@router.get(
    "/geldstrom-api",
    summary="Get Geldstrom API configuration",
    responses={
        200: {"description": "Geldstrom API configuration"},
        403: {"description": "Admin access required"},
        404: {"description": "Not configured"},
    },
)
async def get_geldstrom_api_config(
    _admin: AdminUser,
    factory: RepoFactory,
) -> GeldstromApiConfigResponse:
    """Get Geldstrom API configuration with masked API key."""
    query = GetGeldstromApiConfigQuery.from_factory(factory)
    config = await query.execute()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geldstrom API not configured",
        )

    return GeldstromApiConfigResponse(
        api_key_masked=config.api_key_masked,
        endpoint_url=config.endpoint_url,
        is_active=config.is_active,
        last_updated=config.updated_at,
        last_updated_by=config.updated_by_id,
    )


@router.put(
    "/geldstrom-api",
    summary="Save Geldstrom API configuration",
    responses={
        200: {"description": "Configuration saved"},
        400: {"description": "Invalid configuration or verification failed"},
        403: {"description": "Admin access required"},
    },
)
async def save_geldstrom_api_config(
    request: SaveGeldstromApiConfigRequest,
    _admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
) -> dict[str, str]:
    """Save Geldstrom API key and endpoint. Verifies endpoint health."""
    try:
        command = SaveGeldstromApiConfigCommand.from_factory(factory)
        await command.execute(
            api_key=request.api_key,
            endpoint_url=request.endpoint_url,
        )
        await session.commit()
    except GeldstromApiVerificationError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return {"message": "Geldstrom API configuration saved successfully"}


@router.post(
    "/activate",
    summary="Activate a FinTS provider",
    responses={
        200: {"description": "Provider activated"},
        400: {"description": "Provider not configured"},
        403: {"description": "Admin access required"},
    },
)
async def activate_provider(
    request: ActivateProviderRequest,
    _admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
) -> dict[str, str]:
    """Activate the specified FinTS provider, deactivating the other."""
    try:
        command = ActivateFintsProviderCommand.from_factory(factory)
        await command.execute(FintsProviderMode(request.mode))
    except ProviderNotConfiguredError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    await session.commit()
    return {"message": f"Provider '{request.mode}' activated successfully"}
