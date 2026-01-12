"""
Pytest fixtures for infrastructure persistence tests.

These fixtures provide isolated database sessions for testing.
Each test gets a fresh database with rolled-back transactions.

By default, uses PostgreSQL for realistic testing (matches production).
Set TEST_USE_SQLITE=1 to use SQLite for faster tests without PostgreSQL.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.models.user import UserModel

# Fixed UUIDs for testing - ensures deterministic behavior
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

# Secondary test user for isolation tests
TEST_USER_ID_2 = UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_EMAIL_2 = "test2@example.com"


# Database configuration
# Use PostgreSQL by default (same as production) to catch type/timezone issues
# Set TEST_USE_SQLITE=1 to use SQLite for faster tests without PostgreSQL
USE_SQLITE = os.environ.get("TEST_USE_SQLITE", "").lower() in ("1", "true", "yes")


def _build_postgres_url() -> str:
    """Build PostgreSQL URL from environment variables."""
    # Allow full URL override for CI/CD
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url

    # Build from components (same env vars as production)
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "swen")
    password = os.environ.get("POSTGRES_PASSWORD", "swen_secret")
    db = os.environ.get("POSTGRES_DB", "swen")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


POSTGRES_TEST_URL = _build_postgres_url()


@dataclass(frozen=True)
class MockUserContext:
    """Mock UserContext for testing."""

    user_id: UUID
    email: str = TEST_USER_EMAIL


@pytest.fixture
def user_context():
    """Provide a test UserContext for repository tests."""
    return MockUserContext(user_id=TEST_USER_ID)


def _create_test_user(user_id: UUID, email: str) -> UserModel:
    """Create a test user model with all required fields."""
    now = datetime.now(tz=timezone.utc)
    return UserModel(
        id=user_id,
        email=email,
        auto_post_transactions=False,
        default_currency="EUR",
        show_draft_transactions=True,
        default_date_range_days=30,
        ai_enabled=True,
        ai_model_name="test-model",
        ai_min_confidence=0.7,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(scope="session")
def async_engine():
    """
    Create an async engine for the test database.

    Uses PostgreSQL by default for realistic testing that catches
    datetime timezone issues and type mismatches.
    Set TEST_USE_SQLITE=1 to use SQLite for faster tests.
    """
    if USE_SQLITE:
        # SQLite in-memory database - faster but less strict
        return create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            future=True,
        )
    # PostgreSQL - same behavior as production
    # Use NullPool to avoid connection pool issues in tests
    return create_async_engine(
        POSTGRES_TEST_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
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

    This ensures complete test isolation.
    """
    # Create all tables
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
