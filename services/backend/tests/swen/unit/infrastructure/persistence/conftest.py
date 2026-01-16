"""
Pytest fixtures for infrastructure persistence tests.

These fixtures provide isolated database sessions for testing.
Each test gets a fresh database with rolled-back transactions.

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
This ensures tests NEVER connect to production databases.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen_identity.infrastructure.persistence.sqlalchemy.models import UserModel

# Import Testcontainers fixtures from shared location
from tests.shared.fixtures.database import (
    TEST_USER_EMAIL,
    TEST_USER_ID,
    async_engine,
    postgres_container,
)

# Make fixtures available
__all__ = ["async_engine", "postgres_container"]

# Secondary test user for isolation tests
TEST_USER_ID_2 = UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_EMAIL_2 = "test2@example.com"


@dataclass(frozen=True)
class MockCurrentUser:
    """Mock CurrentUser for testing."""

    user_id: UUID
    email: str = TEST_USER_EMAIL


@pytest.fixture
def current_user():
    """Provide a test CurrentUser for repository tests."""
    return MockCurrentUser(user_id=TEST_USER_ID)


def _create_test_user(user_id: UUID, email: str) -> UserModel:
    """Create a test user model with all required fields.

    Note: UserModel now only contains identity fields (id, email, role).
    User settings are stored separately in user_settings table.
    """
    now = datetime.now(tz=timezone.utc)
    return UserModel(
        id=user_id,
        email=email,
        role="user",
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine):
    """
    Create a fresh database session for each test.

    This fixture:
    1. Creates all tables before each test
    2. Creates test users for FK constraint satisfaction
    3. Provides an isolated session
    4. Rolls back all changes after the test
    5. Drops all tables after the test

    Uses Testcontainers PostgreSQL - never connects to production.
    """
    # Import models to register them with Base.metadata
    import swen.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    import swen_identity.infrastructure.persistence.sqlalchemy.models  # noqa: F401

    # Create all tables (Base.metadata includes both swen and swen_identity tables)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session for the test with pre-seeded test data
    async with async_session_maker() as session:
        # Create test users to satisfy foreign key constraints
        test_user_1 = _create_test_user(TEST_USER_ID, TEST_USER_EMAIL)
        test_user_2 = _create_test_user(TEST_USER_ID_2, TEST_USER_EMAIL_2)
        session.add(test_user_1)
        session.add(test_user_2)
        await session.commit()

        yield session
        # Rollback any uncommitted changes
        await session.rollback()

    # Drop all tables after test
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_session_with_transaction(async_engine):
    """
    Alternative fixture that uses nested transactions for even faster tests.

    This is useful when you want to test rollback behavior explicitly.
    """
    # Import models to register them with Base.metadata
    import swen.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    import swen_identity.infrastructure.persistence.sqlalchemy.models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        # Create test users to satisfy foreign key constraints
        test_user_1 = _create_test_user(TEST_USER_ID, TEST_USER_EMAIL)
        test_user_2 = _create_test_user(TEST_USER_ID_2, TEST_USER_EMAIL_2)
        session.add(test_user_1)
        session.add(test_user_2)
        await session.commit()

    async with async_session_maker() as session, session.begin():
        yield session
        await session.rollback()

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
