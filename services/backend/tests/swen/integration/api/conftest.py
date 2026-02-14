"""Pytest fixtures for API integration tests.

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
This ensures tests never touch production databases.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.presentation.api.app import API_V1_PREFIX, create_app
from swen.presentation.api.dependencies import get_db_session
from swen_config.settings import Settings, get_settings

# Re-export shared fixtures from database.py
from tests.shared.fixtures.database import (
    TEST_USER_EMAIL,
    TEST_USER_EMAIL_2,
    TEST_USER_ID,
    TEST_USER_ID_2,
    async_engine,
    postgres_container,
)

# Make fixtures available to tests in this directory
__all__ = ["postgres_container", "async_engine"]

# Generate a valid Fernet key for testing
TEST_ENCRYPTION_KEY = Fernet.generate_key()


@pytest.fixture
def api_v1_prefix() -> str:
    """Get the API v1 prefix for building URLs."""
    return API_V1_PREFIX


@pytest.fixture
def api_settings() -> Settings:
    """Test API settings with debug enabled."""
    return Settings(
        # Required security settings
        encryption_key=SecretStr(TEST_ENCRYPTION_KEY.decode()),
        jwt_secret_key=SecretStr("test-jwt-secret-for-testing-only"),
        postgres_password=SecretStr("test-password"),
        # API settings
        api_host="127.0.0.1",
        api_port=8000,
        api_debug=True,
        api_cors_origins="http://localhost:3000",
        api_cookie_secure=False,  # Allow HTTP in tests
        # Enable open registration for tests
        registration_mode="open",
    )


@pytest.fixture
def mock_encryption_key():
    """Mock the encryption key for API tests.

    This fixture patches get_encryption_key to return a valid test key.
    The patch remains active for the duration of the test.
    """
    with patch(
        "swen.presentation.api.dependencies.get_encryption_key",
        return_value=TEST_ENCRYPTION_KEY,
    ):
        yield TEST_ENCRYPTION_KEY


def _setup_test_database(async_engine):
    """Synchronously set up the test database with tables and seed data.

    This runs in a fresh event loop to avoid conflicts with TestClient's loop.
    """
    # Import models to register them with Base.metadata
    import swen.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    import swen_identity.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    from swen_identity.infrastructure.persistence.sqlalchemy.models import UserModel

    async def _setup():
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # Seed test users
        session_maker = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_maker() as session:
            now = datetime.now(tz=timezone.utc)
            user1 = UserModel(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                role="user",
                created_at=now,
                updated_at=now,
            )
            user2 = UserModel(
                id=TEST_USER_ID_2,
                email=TEST_USER_EMAIL_2,
                role="user",
                created_at=now,
                updated_at=now,
            )
            session.add(user1)
            session.add(user2)
            await session.commit()

    # Run in a fresh event loop to avoid conflicts
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_setup())
    finally:
        loop.close()


def _teardown_test_database(async_engine):
    """Synchronously tear down the test database."""

    async def _teardown():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_teardown())
    finally:
        loop.close()


@pytest.fixture
def test_client(api_settings, async_engine, mock_encryption_key):
    """Create a test client with Testcontainers PostgreSQL.

    Sets up the database synchronously, then lets FastAPI manage its own
    session creation within the TestClient's event loop context.
    """
    # Set up database (synchronously, with fresh event loop)
    _setup_test_database(async_engine)

    app = create_app(settings=api_settings)

    # Create session factory for the test engine
    test_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Override the database session dependency
    async def override_get_db_session():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Override settings to use test settings
    app.dependency_overrides[get_settings] = lambda: api_settings

    yield TestClient(app)

    # Tear down database after test
    _teardown_test_database(async_engine)


@pytest.fixture
def registered_user_data():
    """Test user registration data.

    Note: Uses a different email than the pre-seeded test users
    (test@example.com, test2@example.com) to avoid conflicts.
    """
    return {
        "email": "api-test-user@example.com",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def auth_headers(test_client, registered_user_data, api_v1_prefix) -> dict:
    """Get auth headers for a registered user."""
    # Register the user
    response = test_client.post(
        f"{api_v1_prefix}/auth/register",
        json=registered_user_data,
    )
    assert response.status_code == 201, (
        f"Registration failed: {response.status_code} - {response.text}"
    )

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authenticated_user(test_client, registered_user_data, api_v1_prefix) -> dict:
    """Get authenticated user data with headers and credentials.

    Returns a dict compatible with tests expecting:
    - headers: Authorization headers with Bearer token
    - email: User's email
    - password: User's password
    - user_id: User's ID from registration response
    """
    # Register the user
    response = test_client.post(
        f"{api_v1_prefix}/auth/register",
        json=registered_user_data,
    )
    assert response.status_code == 201, (
        f"Registration failed: {response.status_code} - {response.text}"
    )

    data = response.json()
    token = data["access_token"]
    # User info is nested under 'user' key
    user_id = data["user"]["id"]

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "email": registered_user_data["email"],
        "password": registered_user_data["password"],
        "user_id": user_id,
    }


# ============================================================================
# Admin-specific fixtures (empty database, admin_only registration mode)
# ============================================================================


def _setup_empty_database(async_engine):
    """Set up database with tables but NO seeded users.

    Used for admin tests where first registered user should become admin.
    """
    # Import models to register them with Base.metadata
    import swen.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    import swen_identity.infrastructure.persistence.sqlalchemy.models  # noqa: F401

    async def _setup():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        # No user seeding - empty database

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_setup())
    finally:
        loop.close()


@pytest.fixture
def admin_api_settings() -> Settings:
    """Test API settings for admin tests with admin_only registration."""
    return Settings(
        encryption_key=SecretStr(TEST_ENCRYPTION_KEY.decode()),
        jwt_secret_key=SecretStr("test-jwt-secret-for-testing-only"),
        postgres_password=SecretStr("test-password"),
        api_host="127.0.0.1",
        api_port=8000,
        api_debug=True,
        api_cors_origins="http://localhost:3000",
        api_cookie_secure=False,
        # Admin-only registration (first user becomes admin)
        registration_mode="admin_only",
    )
