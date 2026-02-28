"""Admin FinTS configuration endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from swen.application.commands.system import (
    UpdateFinTSProductIDCommand,
    UploadFinTSInstituteCSVCommand,
)
from swen.application.queries.system import (
    GetFinTSConfigurationQuery,
    GetFinTSConfigurationStatusQuery,
)
from swen.domain.shared.exceptions import ConflictError
from swen.infrastructure.system.fints_configuration_service import (
    FinTSConfigurationService,
)
from swen.presentation.api.dependencies import (
    AdminUser,
    DBSession,
    RepoFactory,
)
from swen.presentation.api.schemas.fints_config import (
    ConfigStatusResponse,
    FinTSConfigResponse,
    MessageResponse,
    SaveInitialConfigResponse,
    UpdateProductIDRequest,
    UploadCSVResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fints_config", tags=["admin-fints"])


@router.get(
    "/configuration",
    summary="Get FinTS configuration",
    responses={
        200: {"description": "Current configuration"},
        403: {"description": "Admin access required"},
        404: {"description": "Configuration not set"},
    },
)
async def get_fints_configuration(
    _admin: AdminUser,
    factory: RepoFactory,
) -> FinTSConfigResponse:
    """Get current FinTS configuration (admin only)."""
    query = GetFinTSConfigurationQuery.from_factory(factory)
    config = await query.execute()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FinTS configuration not set",
        )

    return FinTSConfigResponse(
        product_id_masked=config.product_id_masked,
        csv_institute_count=config.csv_institute_count,
        csv_file_size_kb=config.csv_file_size_bytes // 1024,
        last_updated=config.updated_at,
        last_updated_by=config.updated_by_id,
    )


@router.put(
    "/product-id",
    summary="Update FinTS Product ID",
    responses={
        200: {"description": "Product ID updated"},
        400: {"description": "Invalid Product ID"},
        403: {"description": "Admin access required"},
    },
)
async def update_product_id(
    request: UpdateProductIDRequest,
    _admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
) -> MessageResponse:
    """Update FinTS Product ID (admin only)."""
    try:
        command = UpdateFinTSProductIDCommand.from_factory(factory)
        await command.execute(request.product_id)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MessageResponse(message="Product ID updated successfully")


@router.post(
    "/csv",
    summary="Upload FinTS institute CSV",
    responses={
        200: {"description": "CSV uploaded successfully"},
        400: {"description": "Invalid CSV file"},
        403: {"description": "Admin access required"},
        413: {"description": "File too large"},
    },
)
async def upload_csv(
    file: UploadFile,
    _admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
) -> UploadCSVResponse:
    """Upload FinTS institute directory CSV (admin only)."""
    content = await file.read()

    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)",
        )

    try:
        command = UploadFinTSInstituteCSVCommand.from_factory(factory)
        result = await command.execute(content)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return UploadCSVResponse(
        message="CSV uploaded successfully",
        institute_count=result.institute_count,
        file_size_kb=result.file_size_bytes // 1024,
    )


@router.get(
    "/status",
    summary="Check FinTS configuration status",
    responses={
        200: {"description": "Configuration status"},
    },
)
async def get_configuration_status(
    _admin: AdminUser,
    factory: RepoFactory,
) -> ConfigStatusResponse:
    """Check if FinTS is configured (admin only)."""
    query = GetFinTSConfigurationStatusQuery.from_factory(factory)
    result = await query.execute()

    return ConfigStatusResponse(
        is_configured=result.is_configured,
        message=result.message,
    )


@router.post(
    "/initial",
    summary="Save initial FinTS configuration",
    responses={
        200: {"description": "Initial configuration saved"},
        400: {"description": "Invalid configuration"},
        403: {"description": "Admin access required"},
        409: {"description": "Configuration already exists"},
    },
)
async def save_initial_configuration(
    file: UploadFile,
    admin: AdminUser,
    session: DBSession,
    factory: RepoFactory,
    product_id: Annotated[str, Form(min_length=1, max_length=100)],
) -> SaveInitialConfigResponse:
    """Save FinTS configuration (Product ID + CSV). Creates or updates."""
    csv_content = await file.read()

    if len(csv_content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)",
        )

    try:
        service = FinTSConfigurationService(
            repository=factory.fints_config_repository(),
        )
        config = await service.save_initial_configuration(
            product_id=product_id,
            csv_content=csv_content,
            admin_user_id=admin.id,
        )
        await session.commit()
    except ConflictError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ValueError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return SaveInitialConfigResponse(
        message="Initial FinTS configuration saved successfully",
        institute_count=config.csv_institute_count,
        file_size_kb=config.csv_file_size_bytes // 1024,
    )
