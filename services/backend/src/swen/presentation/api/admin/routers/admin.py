import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from swen.presentation.api.admin.routers.admin_fints_config import (
    router as fints_config_router,
)
from swen.presentation.api.admin.routers.admin_fints_provider import (
    router as fints_provider_router,
)
from swen.presentation.api.admin.schemas.admin import (
    CreateUserRequest,
    UpdateRoleRequest,
    UserSummaryResponse,
)
from swen.presentation.api.dependencies import (
    AdminUserDep,
    DBSessionDep,
    IdentityAdapterFactoryDep,
    IdentityRepoFactoryDep,
)
from swen_identity import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    EmailAlreadyExistsError,
    UserNotFoundError,
    UserRole,
)
from swen_identity.application.commands import (
    CreateUserCommand,
    DeleteUserCommand,
    UpdateUserRoleCommand,
)
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserRepositorySQLAlchemy,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include FinTS configuration sub-router
router.include_router(fints_config_router)

# Include FinTS provider management sub-router
router.include_router(fints_provider_router)


@router.get(
    "/users",
    summary="List all users",
    responses={
        200: {"description": "List of all users"},
        403: {"description": "Admin access required"},
    },
)
async def list_users(
    _admin: AdminUserDep,  # Used for authorization check
    session: DBSessionDep,
) -> list[UserSummaryResponse]:
    """List all users."""
    user_repo = UserRepositorySQLAlchemy(session)
    users = await user_repo.list_all()
    return [
        UserSummaryResponse(
            id=u.id,
            email=u.email,
            role=u.role.value,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid role"},
        403: {"description": "Admin access required"},
        409: {"description": "Email already registered"},
    },
)
async def create_user(
    request: CreateUserRequest,
    admin: AdminUserDep,
    factory: IdentityRepoFactoryDep,
    identity_adapter_factory: IdentityAdapterFactoryDep,
) -> UserSummaryResponse:
    """Create a new user."""
    try:
        role = UserRole(request.role.lower())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}. Must be 'user' or 'admin'",
        ) from e

    command = CreateUserCommand.from_factory(factory, identity_adapter_factory)

    try:
        user = await command.execute(
            email=request.email,
            password=request.password,
            role=role,
        )
    except EmailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered",
        ) from e

    logger.info("Admin %s created user: %s", admin.email, request.email)
    return UserSummaryResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    responses={
        204: {"description": "User deleted successfully"},
        400: {"description": "Cannot delete yourself"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: UUID,
    admin: AdminUserDep,
    factory: IdentityRepoFactoryDep,
) -> None:
    """Delete a user."""
    command = DeleteUserCommand.from_factory(factory)

    try:
        await command.execute(user_id=user_id, requesting_admin_id=admin.id)
    except CannotDeleteSelfError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        ) from e
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    logger.info("Admin %s deleted user: %s", admin.email, user_id)


@router.patch(
    "/users/{user_id}/role",
    summary="Update user role",
    responses={
        200: {"description": "Role updated successfully"},
        400: {"description": "Invalid role or cannot demote yourself"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    admin: AdminUserDep,
    factory: IdentityRepoFactoryDep,
) -> UserSummaryResponse:
    """Update a user's role."""
    try:
        new_role = UserRole(request.role.lower())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}. Must be 'user' or 'admin'",
        ) from e

    command = UpdateUserRoleCommand.from_factory(factory)

    try:
        user = await command.execute(
            user_id=user_id,
            new_role=new_role,
            requesting_admin_id=admin.id,
        )
    except CannotDemoteSelfError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself from admin",
        ) from e
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from e

    logger.info(
        "Admin %s changed role of %s to %s",
        admin.email,
        user_id,
        new_role.value,
    )
    return UserSummaryResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
    )
