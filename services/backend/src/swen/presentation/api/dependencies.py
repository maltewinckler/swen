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

from swen.application.context import UserContext
from swen.application.services import AuthenticationService
from swen.domain.user import User
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyRepositoryFactory,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from swen.presentation.api.config import get_api_settings
from swen_auth import InvalidTokenError, JWTService, PasswordHashingService
from swen_auth.persistence.sqlalchemy import UserCredentialRepositorySQLAlchemy
from swen_config.settings import Settings, get_settings

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


# Type alias for injected session
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# -----------------------------------------------------------------------------
# Database Schema Management
# -----------------------------------------------------------------------------


async def create_tables() -> None:
    """
    Create all database tables (idempotent).

    Uses SQLAlchemy's create_all() which only creates missing tables.
    Existing tables and their data are never modified or deleted.
    """
    engine = get_engine()
    logger.info("Ensuring all database tables exist...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database schema is up to date (missing tables created if needed)")


async def drop_tables() -> None:
    """
    Drop all database tables (USE WITH CAUTION!).

    This is primarily for testing and development reset scenarios.
    """
    engine = get_engine()
    logger.warning("Dropping all database tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.info("Database tables dropped successfully")


# -----------------------------------------------------------------------------
# Authentication Services
# -----------------------------------------------------------------------------


def get_jwt_service(
    settings: Settings = Depends(get_api_settings),
) -> JWTService:
    """Get JWT service configured with API settings."""
    return JWTService(
        secret_key=settings.jwt_secret_key.get_secret_value(),
        access_token_expire_hours=settings.jwt_access_token_expire_hours,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
    )


def get_password_service() -> PasswordHashingService:
    """Get password hashing service."""
    return PasswordHashingService()


async def get_authentication_service(
    session: DBSession,
    jwt_service: JWTService = Depends(get_jwt_service),
    password_service: PasswordHashingService = Depends(get_password_service),
) -> AuthenticationService:
    """
    Get authentication service with all dependencies.

    This service orchestrates user registration, login, and token management.
    """
    user_repo = UserRepositorySQLAlchemy(session)
    credential_repo = UserCredentialRepositorySQLAlchemy(session)

    return AuthenticationService(
        user_repository=user_repo,
        credential_repository=credential_repo,
        password_service=password_service,
        jwt_service=jwt_service,
    )


# Type alias for injected auth service
AuthService = Annotated[AuthenticationService, Depends(get_authentication_service)]


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


# Type alias for injected current user
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> User | None:
    """
    Optional authentication dependency.

    Returns the current user if a valid token is provided, None otherwise.
    Useful for endpoints that work differently for authenticated users.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, session, jwt_service)
    except HTTPException:
        return None


# Type alias for optional current user
OptionalCurrentUser = Annotated[User | None, Depends(get_current_user_optional)]


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin user."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type alias for admin user
AdminUser = Annotated[User, Depends(require_admin)]


# -----------------------------------------------------------------------------
# User Context & Repository Factory
# -----------------------------------------------------------------------------


async def get_user_context(
    user: User = Depends(get_current_user),
) -> UserContext:
    """
    Get UserContext for repository scoping.

    The UserContext is used to scope repository queries to the current user.
    """
    return UserContext.create(user)


# Type alias for injected user context
CurrentUserContext = Annotated[UserContext, Depends(get_user_context)]


async def get_repository_factory(
    session: AsyncSession = Depends(get_db_session),
    user_context: UserContext = Depends(get_user_context),
) -> SQLAlchemyRepositoryFactory:
    """
    Get repository factory for the current user.

    The factory creates user-scoped repositories for domain operations.
    """
    return SQLAlchemyRepositoryFactory(
        session=session,
        user_context=user_context,
        encryption_key=get_encryption_key(),
    )


# Type alias for injected repository factory
RepoFactory = Annotated[SQLAlchemyRepositoryFactory, Depends(get_repository_factory)]


# -----------------------------------------------------------------------------
# Application Queries & Services
# -----------------------------------------------------------------------------
# Application layer classes have from_factory() classmethods that encapsulate
# their dependency knowledge. Use them directly in routers:
#
#   async def list_accounts(factory: RepoFactory, ...):
#       query = ListAccountsQuery.from_factory(factory)  # NOQA: ERA001
#
# This avoids trivial wrapper functions and keeps the router explicit about
# what it's using.
