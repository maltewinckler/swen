"""Admin local FinTS configuration endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from swen.application.system.commands import UpdateLocalFinTSConfigCommand
from swen.application.system.queries import (
    GetFinTSConfigurationQuery,
    GetFinTSConfigurationStatusQuery,
)
from swen.presentation.api.admin.schemas.fints_config import (
    ConfigStatusResponse,
    FinTSConfigResponse,
    UpdateLocalFinTSConfigResponse,
)
from swen.presentation.api.dependencies import (
    AdminUser,
    DBSession,
    RepoFactory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local_fints_configuration", tags=["admin-local-fints"])


@router.get(
    "",
    summary="Get local FinTS configuration",
    responses={
        200: {"description": "Current configuration"},
        403: {"description": "Admin access required"},
        404: {"description": "Configuration not set"},
    },
)
async def get_local_fints_configuration(
    _admin: AdminUser,
    factory: RepoFactory,
) -> FinTSConfigResponse:
    """Get current local FinTS configuration (admin only)."""
    query = GetFinTSConfigurationQuery.from_factory(factory)
    config = await query.execute()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local FinTS configuration not set",
        )

    return FinTSConfigResponse(
        product_id_masked=config.product_id_masked,
        csv_institute_count=config.csv_institute_count,
        csv_file_size_kb=config.csv_file_size_bytes // 1024,
        last_updated=config.updated_at,
        last_updated_by=config.updated_by_id,
    )


@router.post(
    "",
    summary="Create or update local FinTS configuration",
    responses={
        200: {"description": "Configuration saved"},
        400: {"description": "Invalid configuration"},
        403: {"description": "Admin access required"},
        413: {"description": "File too large"},
    },
)
async def upsert_local_fints_configuration(
    _admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
    product_id: Annotated[str | None, Form(min_length=1, max_length=100)] = None,
    file: UploadFile | None = None,
) -> UpdateLocalFinTSConfigResponse:
    """Create or update local FinTS configuration (Product ID and/or CSV).

    On first-time setup both ``product_id`` and ``file`` are required.
    After that either field can be updated independently.
    """
    if product_id is None and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of product_id or file must be provided",
        )

    csv_content: bytes | None = None
    if file is not None:
        csv_content = await file.read()
        if len(csv_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (max 10MB)",
            )

    try:
        command = UpdateLocalFinTSConfigCommand.from_factory(factory)
        result = await command.execute(product_id=product_id, csv_content=csv_content)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    file_size_kb = (result.file_size_bytes // 1024) if result.file_size_bytes else None
    return UpdateLocalFinTSConfigResponse(
        message="Local FinTS configuration saved successfully",
        institute_count=result.institute_count,
        file_size_kb=file_size_kb,
    )


@router.get(
    "/status",
    summary="Check local FinTS configuration status",
    responses={
        200: {"description": "Configuration status"},
        403: {"description": "Admin access required"},
    },
)
async def get_local_fints_configuration_status(
    _admin: AdminUser,
    factory: RepoFactory,
) -> ConfigStatusResponse:
    """Check whether local FinTS is configured (admin only)."""
    query = GetFinTSConfigurationStatusQuery.from_factory(factory)
    result = await query.execute()

    return ConfigStatusResponse(
        is_configured=result.is_configured,
        message=result.message,
    )
