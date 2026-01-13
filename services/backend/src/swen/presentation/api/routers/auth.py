"""Authentication router for user registration, login, and token management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from swen.application.services.password_reset_service import PasswordResetService
from swen.domain.user import EmailAlreadyExistsError, User
from swen.infrastructure.email import EmailService
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from swen.presentation.api.config import get_api_settings
from swen.presentation.api.dependencies import (
    AuthService,
    CurrentUser,
    DBSession,
    get_password_service,
)
from swen.presentation.api.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from swen_auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    InvalidTokenError,
    WeakPasswordError,
)
from swen_auth.persistence.sqlalchemy import (
    PasswordResetTokenRepositorySQLAlchemy,
    UserCredentialRepositorySQLAlchemy,
)
from swen_auth.services import PasswordHashingService
from swen_config.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Type aliases for dependencies using Annotated (modern FastAPI pattern)
SettingsDep = Annotated[Settings, Depends(get_api_settings)]
PasswordHashingServiceDep = Annotated[
    PasswordHashingService,
    Depends(get_password_service),
]

# Cookie name for refresh token
REFRESH_TOKEN_COOKIE = "swen_refresh_token"  # NOQA: S105


def _set_refresh_token_cookie(
    response: Response,
    token: str,
    settings: Settings,
) -> None:
    """Set the refresh token as an HttpOnly cookie.

    This cookie is:
    - HttpOnly: Not accessible to JavaScript (XSS protection)
    - Secure: Only sent over HTTPS (when cookie_secure=True)
    - SameSite: Prevents CSRF attacks
    - Path restricted: Only sent to /api/v1/auth endpoints
    """
    max_age_seconds = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=settings.api_cookie_secure,
        samesite=settings.api_cookie_samesite,
        max_age=max_age_seconds,
        path="/api/v1/auth",  # Only sent to auth endpoints
        domain=settings.api_cookie_domain,
    )


def _clear_refresh_token_cookie(response: Response, settings: Settings) -> None:
    """Clear the refresh token cookie (for logout)."""
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/api/v1/auth",
        domain=settings.api_cookie_domain,
    )


def _create_auth_response(
    user: User,
    access_token: str,
    settings: Settings,
) -> AuthResponse:
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
        ),
        access_token=access_token,
        refresh_token=None,
        expires_in=settings.jwt_access_token_expire_hours * 3600,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Invalid input (weak password)"},
        403: {"description": "Registration disabled"},
        409: {"description": "Email already registered"},
    },
)
async def register(
    request: RegisterRequest,
    response: Response,
    auth_service: AuthService,
    session: DBSession,
    settings: SettingsDep,
) -> AuthResponse:
    # Check registration mode (first user is always allowed)
    if settings.registration_mode == "admin_only":
        user_repo = UserRepositorySQLAlchemy(session)
        user_count = await user_repo.count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is disabled. Contact an administrator.",
            )

    try:
        user, access_token, new_refresh_token = await auth_service.register(
            email=request.email,
            password=request.password,
        )
        await session.commit()

        _set_refresh_token_cookie(response, new_refresh_token, settings)

        logger.info("New user registered: %s", request.email)
        return _create_auth_response(user, access_token, settings)

    except EmailAlreadyExistsError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered",
        ) from e
    except WeakPasswordError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet security requirements",
        ) from e
    except Exception as e:
        await session.rollback()
        logger.exception("Registration failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from e


@router.post(
    "/login",
    summary="Authenticate user",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        423: {"description": "Account locked"},
    },
)
async def login(
    request: LoginRequest,
    response: Response,
    auth_service: AuthService,
    session: DBSession,
    settings: SettingsDep,
) -> AuthResponse:
    """
    Authenticate with email and password.

    Returns an access token on successful authentication.
    The refresh token is set as an HttpOnly cookie for security.

    Account will be locked after multiple failed attempts.
    """
    try:
        user, access_token, new_refresh_token = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        await session.commit()

        # Set refresh token as HttpOnly cookie
        _set_refresh_token_cookie(response, new_refresh_token, settings)

        return _create_auth_response(user, access_token, settings)

    except InvalidCredentialsError as e:
        await session.commit()  # Commit failed attempt count
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from e
    except AccountLockedError as e:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked due to too many failed attempts",
        ) from e
    except Exception as e:
        await session.rollback()
        logger.exception("Login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        ) from e


@router.post(
    "/refresh",
    summary="Refresh access token",
    responses={
        200: {"description": "Tokens refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    response: Response,
    auth_service: AuthService,
    settings: SettingsDep,
    request: RefreshRequest | None = None,
    refresh_token_cookie: Annotated[
        str | None,
        Cookie(alias=REFRESH_TOKEN_COOKIE),
    ] = None,
) -> TokenResponse:
    """
    Get a new access token using a valid refresh token.

    The refresh token can be provided either:
    - In the request body (legacy, for backward compatibility)
    - Via HttpOnly cookie (preferred, automatic)

    A new refresh token is set as an HttpOnly cookie (token rotation).
    """
    # Get refresh token from body or cookie
    token = None
    if request and request.refresh_token:
        token = request.refresh_token
    elif refresh_token_cookie:
        token = refresh_token_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    try:
        access_token, new_refresh_token = await auth_service.refresh_token(
            refresh_token=token,
        )

        # Set new refresh token as HttpOnly cookie (rotation)
        _set_refresh_token_cookie(response, new_refresh_token, settings)

        expires_in_seconds = settings.jwt_access_token_expire_hours * 3600
        return TokenResponse(
            access_token=access_token,
            refresh_token=None,  # Now sent via HttpOnly cookie
            expires_in=expires_in_seconds,
        )

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from e


@router.get(
    "/me",
    summary="Get current user",
    responses={
        200: {"description": "Current user data"},
        401: {"description": "Not authenticated"},
    },
)
async def get_me(user: CurrentUser) -> UserResponse:
    """
    Get the current authenticated user's information.

    Requires a valid access token in the Authorization header.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    responses={
        204: {"description": "Password changed successfully"},
        400: {"description": "New password too weak"},
        401: {"description": "Current password incorrect or not authenticated"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    user: CurrentUser,
    auth_service: AuthService,
    session: DBSession,
) -> None:
    """
    Change the current user's password.

    Requires the current password for verification and a new password
    that meets the strength requirements.
    """
    try:
        await auth_service.change_password(
            user_id=user.id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
        await session.commit()

        logger.info("Password changed for user: %s", user.email)

    except InvalidCredentialsError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from e
    except WeakPasswordError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet security requirements",
        ) from e
    except Exception as e:
        await session.rollback()
        logger.exception("Password change failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        ) from e


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    responses={
        204: {"description": "Logged out successfully"},
    },
)
async def logout(
    response: Response,
    settings: SettingsDep,
) -> None:
    """Logout user."""
    _clear_refresh_token_cookie(response, settings)
    logger.debug("User logged out (refresh token cookie cleared)")


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request password reset",
    responses={
        202: {"description": "If the email exists, a reset link has been sent"},
    },
)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: DBSession,
    settings: SettingsDep,
    password_service: PasswordHashingServiceDep,
) -> dict:
    """Request a password reset email."""
    user_repo = UserRepositorySQLAlchemy(session)
    token_repo = PasswordResetTokenRepositorySQLAlchemy(session)
    credential_repo = UserCredentialRepositorySQLAlchemy(session)
    email_service = EmailService(settings)

    service = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        credential_repository=credential_repo,
        password_service=password_service,
        email_service=email_service,
        frontend_base_url=settings.frontend_base_url,
    )

    await service.request_reset(request.email)
    await session.commit()

    return {"message": "If the email exists, a reset link has been sent."}


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset password with token",
    responses={
        204: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired token"},
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    session: DBSession,
    settings: SettingsDep,
    password_service: PasswordHashingServiceDep,
) -> None:
    """Reset password with a token."""
    user_repo = UserRepositorySQLAlchemy(session)
    token_repo = PasswordResetTokenRepositorySQLAlchemy(session)
    credential_repo = UserCredentialRepositorySQLAlchemy(session)
    email_service = EmailService(settings)

    service = PasswordResetService(
        user_repository=user_repo,
        token_repository=token_repo,
        credential_repository=credential_repo,
        password_service=password_service,
        email_service=email_service,
        frontend_base_url=settings.frontend_base_url,
    )

    try:
        await service.reset_password(
            token=request.token,
            new_password=request.new_password,
        )
        await session.commit()
        logger.info("Password reset completed")

    except InvalidResetTokenError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        ) from e
    except WeakPasswordError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet security requirements",
        ) from e
