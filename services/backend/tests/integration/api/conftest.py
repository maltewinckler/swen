"""Pytest fixtures for API integration tests."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swen.infrastructure.persistence.sqlalchemy.models import Base
from swen.presentation.api.app import API_V1_PREFIX, create_app
from swen.presentation.api.dependencies import get_db_session
from swen_auth.persistence.sqlalchemy import AuthBase
from swen_config.settings import Settings


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
    )


@pytest.fixture
async def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        # Create all tables (both swen and swen_auth)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(AuthBase.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create a test database session."""
    session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session


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


@pytest.fixture
def test_client(api_settings, test_db_engine, mock_encryption_key) -> TestClient:
    """Create a test client with an in-memory database."""
    app = create_app(settings=api_settings)

    # Create a session maker that uses our test engine
    test_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Override the database session dependency
    async def override_get_db_session():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    return TestClient(app)


@pytest.fixture
def registered_user_data():
    """Test user registration data."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def auth_headers(test_client, registered_user_data, api_v1_prefix) -> dict:
    """Get auth headers for a registered user."""
    # Register the user
    response = test_client.post(
        f"{api_v1_prefix}/auth/register", json=registered_user_data
    )
    assert response.status_code == 201

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
