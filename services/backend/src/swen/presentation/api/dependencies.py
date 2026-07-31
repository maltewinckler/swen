"""FastAPI dependency injection for the SWEN API.

Provides dependencies for:
- Database sessions
- Authentication (current user from JWT)
- User context for repository scoping
- Service instances
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from swen.application.ports.ml_service import MLServicePort
from swen.infrastructure.adapters.identity import IdentityAdapter
from swen.infrastructure.integration.ml import (
    MLServiceAdapter,
    MLServiceClient,
)
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyRepositoryFactory,
)
from swen_config.settings import Settings, get_settings
from swen_identity import (
    InvalidTokenError,
    JWTService,
    PasswordHashingService,
    User,
)
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserRepositorySQLAlchemy,
)
from swen_identity.infrastructure.persistence.sqlalchemy.repository_factory import (
    RepositoryFactorySQLAlchemy as IdentityRepositoryFactorySQLAlchemy,
)

logger = logging.getLogger(__name__)

# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)


@lru_cache()
def get_database_url() -> str:
    """
    Get database URL from application settings.

    Returns
    -------
    Database URL string
    """
    url = get_settings().database_url

    # Ensure data directory exists for SQLite
    if url.startswith("sqlite"):
        db_path = url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return url


@lru_cache()
def get_encryption_key() -> bytes:
    """
    Get encryption key from application settings as bytes.

    Returns
    -------
    Encryption key as bytes

    Raises
    ------
    ValueError
        If encryption key not configured

    Examples
    --------
    >>> key = get_encryption_key()
    """
    secret = get_settings().encryption_key
    key_value = secret.get_secret_value()
    if not key_value:
        msg = (
            "Encryption key not configured in config.yaml. "
            "Update your application configuration file with a valid Fernet key."
        )
        raise ValueError(msg)

    return key_value.encode()


# -----------------------------------------------------------------------------
# Database Engine & Session (Singleton)
# -----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """
    Get the shared async database engine (singleton).

    The engine manages the connection pool and is reused across all requests.
    This avoids the overhead of creating a new engine per request.

    Returns
    -------
    AsyncEngine instance
    """
    return create_async_engine(
        get_database_url(),
        echo=False,
        pool_pre_ping=True,  # Verify connections before use
    )


@lru_cache(maxsize=1)
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get the shared async session maker (singleton).

    Returns
    -------
    async_sessionmaker configured with the shared engine
    """
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.

    Creates an async session for the request using the shared engine/pool.

    Yields
    ------
    AsyncSession for database operations
    """
    async with get_session_maker()() as session:
        yield session


def get_jwt_service(settings: Settings = Depends(get_settings)) -> JWTService:
    """Get JWT service configured with API settings."""
    return JWTService(
        secret_key=settings.jwt_secret_key.get_secret_value(),
        access_token_expire_hours=settings.jwt_access_token_expire_hours,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
    )


def get_password_service() -> PasswordHashingService:
    """Get password hashing service."""
    return PasswordHashingService()


# -----------------------------------------------------------------------------
# Current User (JWT Authentication)
# -----------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> User:
    """
    FastAPI dependency to get the current authenticated user from JWT.

    Extracts and validates the JWT token from the Authorization header,
    then loads the corresponding User from the database.

    Parameters
    ----------
    credentials
        Bearer token from Authorization header
    session
        Database session
    jwt_service
        JWT service for token verification

    Returns
    -------
    The authenticated User

    Raises
    ------
    HTTPException
        401 if token is missing, invalid, or user not found
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt_service.verify_token(token)
    except InvalidTokenError as e:
        logger.warning("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Reject refresh tokens - they should only be used at /auth/refresh
    if not payload.is_access_token():
        logger.warning(
            "Refresh token used as access token for user: %s",
            payload.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    user_repo = UserRepositorySQLAlchemy(session)
    user = await user_repo.find_by_id(payload.user_id)

    if user is None:
        logger.warning("User not found for token: %s", payload.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin user."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# -----------------------------------------------------------------------------
# User Context & Repository Factory
# -----------------------------------------------------------------------------


async def get_repository_factory(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> SQLAlchemyRepositoryFactory:
    """Get repository factory for the current user."""
    from swen_identity import UserContext  # noqa: PLC0415

    current_user = IdentityAdapter.to_current_user(UserContext.create(user))
    return SQLAlchemyRepositoryFactory(
        session=session,
        current_user=current_user,
        encryption_key=get_encryption_key(),
    )


async def get_identity_repository_factory(
    session: AsyncSession = Depends(get_db_session),
) -> IdentityRepositoryFactorySQLAlchemy:
    """Get swen_identity's repository factory for the current request."""
    return IdentityRepositoryFactorySQLAlchemy(session=session)


# -----------------------------------------------------------------------------
# ML Service (Singleton)
# -----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_ml_client() -> MLServiceClient:
    """Get the shared ML service client (singleton)."""
    settings = get_settings()
    return MLServiceClient(
        base_url=settings.ml_service_url,
        timeout=settings.ml_service_timeout,
        enabled=settings.ml_service_enabled,
    )


@lru_cache(maxsize=1)
def get_ml_port() -> MLServicePort | None:
    """Get the ML service port for application layer (singleton)."""
    settings = get_settings()
    if not settings.ml_service_enabled:
        return None
    return MLServiceAdapter(client=get_ml_client())


# DB session
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
# Settings Dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]
# Encryption and PW dependeicyues
JWTServiceDep = Annotated[JWTService, Depends(get_jwt_service)]
PasswordHashingServiceDep = Annotated[
    PasswordHashingService,
    Depends(get_password_service),
]

# User + Admin auth dependencies
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]

# Repository factories
RepoFactory = Annotated[SQLAlchemyRepositoryFactory, Depends(get_repository_factory)]
IdentityRepoFactory = Annotated[
    IdentityRepositoryFactorySQLAlchemy, Depends(get_identity_repository_factory)
]

# ML service dependencies TODO: Tihnk about unification of these two.
MLClient = Annotated[MLServiceClient, Depends(get_ml_client)]
MLPort = Annotated[MLServicePort | None, Depends(get_ml_port)]
