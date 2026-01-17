"""Fixtures for admin endpoint tests.

Admin tests need a special setup:
- Empty database (no pre-seeded users)
- admin_only registration mode (first user becomes admin)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swen.presentation.api.app import create_app
from swen.presentation.api.dependencies import get_db_session
from swen_config.settings import get_settings

# Import shared fixtures
from tests.swen.integration.api.conftest import (
    _setup_empty_database,
    _teardown_test_database,
    api_v1_prefix,
    async_engine,
    postgres_container,
)

# Re-export for pytest discovery
__all__ = [
    "postgres_container",
    "async_engine",
    "api_v1_prefix",
]


@pytest.fixture
def test_client(admin_api_settings, async_engine, mock_encryption_key):
    """Create a test client for admin tests with empty database.

    Uses admin_only registration mode and no pre-seeded users,
    so the first registered user becomes an admin.
    """
    # Set up empty database (no seeded users)
    _setup_empty_database(async_engine)

    app = create_app(settings=admin_api_settings)

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

    # Override settings to use admin test settings
    app.dependency_overrides[get_settings] = lambda: admin_api_settings

    yield TestClient(app)

    # Tear down database after test
    _teardown_test_database(async_engine)
