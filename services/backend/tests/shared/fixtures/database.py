"""
Testcontainers-based PostgreSQL fixtures for integration tests.

Provides isolated, ephemeral Postgres instances for each test session.
All integration tests should use these fixtures for database access.

Usage:
    # In your test file or conftest.py
    from tests.shared.fixtures.database import db_session

    async def test_something(db_session):
        # db_session is a fresh AsyncSession connected to an ephemeral Postgres
        repo = SomeRepository(db_session)
        await repo.save(entity)
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from swen.infrastructure.persistence.sqlalchemy.models.base import Base

# Use same Postgres version as production
POSTGRES_IMAGE = "postgres:18-alpine"

# Fixed UUIDs for testing - ensures deterministic behavior
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

# Secondary test user for isolation tests
TEST_USER_ID_2 = UUID("00000000-0000-0000-0000-000000000002")
TEST_USER_EMAIL_2 = "test2@example.com"


@pytest.fixture(scope="session")
def postgres_container():
    """
    Start a PostgreSQL container for the test session.

    The container is shared across all tests in the session for performance.
    Each test gets a clean database state via table drop/create.

    The container is automatically cleaned up when the session ends.
    """
    with PostgresContainer(POSTGRES_IMAGE) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def async_engine(postgres_container):
    """
    Create an async SQLAlchemy engine connected to the test container.

    Session-scoped to avoid recreating the engine for each test.
    """
    # Get the connection URL and convert to asyncpg format
    connection_url = postgres_container.get_connection_url()
    # Testcontainers may return postgresql+psycopg2:// or postgresql://
    async_url = connection_url.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

    return create_async_engine(
        async_url,
        echo=False,
        future=True,
        poolclass=NullPool,  # Avoid connection pool issues in tests
    )


def _create_test_user(user_id: UUID, email: str):
    """Create a test user model with all required fields.

    Note: UserModel now only contains identity fields (id, email, role).
    User settings are stored separately in user_settings table.
    """
    # Import here to avoid circular imports
    from swen_identity.infrastructure.persistence.sqlalchemy.models import UserModel

    now = datetime.now(tz=timezone.utc)
    return UserModel(
        id=user_id,
        email=email,
        role="user",
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine):
    """
    Provide an isolated database session for each test.

    This fixture:
    1. Drops all tables (clean slate)
    2. Creates all tables
    3. Seeds required test users (for FK constraints)
    4. Yields an isolated session
    5. Rolls back any uncommitted changes after the test
    6. Drops all tables after the test

    This ensures complete test isolation - each test starts fresh.
    """
    # Import models to register them with Base.metadata
    import swen.infrastructure.persistence.sqlalchemy.models  # noqa: F401
    import swen_identity.infrastructure.persistence.sqlalchemy.models  # noqa: F401

    # Create all tables (drop first to ensure clean state)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session for the test with pre-seeded test data
    async with session_maker() as session:
        # Create test users to satisfy foreign key constraints
        test_user_1 = _create_test_user(TEST_USER_ID, TEST_USER_EMAIL)
        test_user_2 = _create_test_user(TEST_USER_ID_2, TEST_USER_EMAIL_2)
        session.add(test_user_1)
        session.add(test_user_2)
        await session.commit()

        yield session

        # Rollback any uncommitted changes
        await session.rollback()

    # Drop all tables after test (clean up)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
