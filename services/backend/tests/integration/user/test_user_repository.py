"""Integration tests for UserRepository with SQLite."""

from uuid import UUID, uuid4

import pytest
from swen.domain.user import (
    User,
    UserPreferences,
    EmailAlreadyExistsError,
)
from swen.infrastructure.persistence.sqlalchemy.models import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def session():
    """Create an in-memory SQLite session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session


@pytest.fixture
def user_repo(session):
    """Create UserRepository instance."""
    return UserRepositorySQLAlchemy(session)


TEST_EMAIL = "test@example.com"


class TestUserRepositorySQLAlchemy:
    """Integration tests for UserRepositorySQLAlchemy."""

    @pytest.mark.asyncio
    async def test_save_and_find_by_id(self, user_repo, session):
        """Can save and retrieve a user by ID."""
        user = User.create(TEST_EMAIL)

        await user_repo.save(user)
        await session.flush()

        found = await user_repo.find_by_id(user.id)

        assert found is not None
        assert found.id == user.id
        assert isinstance(found.id, UUID)
        assert found.email == TEST_EMAIL
        assert found.preferences == UserPreferences()

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, user_repo):
        """Returns None for non-existent user."""
        random_id = uuid4()

        found = await user_repo.find_by_id(random_id)

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email(self, user_repo, session):
        """Can find user by email."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)

        assert found is not None
        assert found.email == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_find_by_email_case_insensitive(self, user_repo, session):
        """find_by_email is case insensitive."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        found = await user_repo.find_by_email("TEST@EXAMPLE.COM")

        assert found is not None
        assert found.email == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(self, user_repo):
        """Returns None for non-existent email."""
        found = await user_repo.find_by_email("nonexistent@example.com")

        assert found is None

    @pytest.mark.asyncio
    async def test_exists_by_email(self, user_repo, session):
        """exists_by_email returns True for existing user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        exists = await user_repo.exists_by_email(TEST_EMAIL)

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_email_not_found(self, user_repo):
        """exists_by_email returns False for non-existent user."""
        exists = await user_repo.exists_by_email("nonexistent@example.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_get_or_create_by_email_creates(self, user_repo, session):
        """get_or_create_by_email creates user if not exists."""
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        await session.flush()

        assert user.email == TEST_EMAIL
        assert isinstance(user.id, UUID)
        assert user.preferences == UserPreferences()

        # Should be persisted
        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is not None
        assert found.id == user.id  # Same ID

    @pytest.mark.asyncio
    async def test_get_or_create_by_email_returns_existing(self, user_repo, session):
        """get_or_create_by_email returns existing user."""
        # Create user first
        original = await user_repo.get_or_create_by_email(TEST_EMAIL)
        original.update_preferences(auto_post_transactions=True)
        await user_repo.save(original)
        await session.flush()

        # Get again
        retrieved = await user_repo.get_or_create_by_email(TEST_EMAIL)

        assert retrieved.id == original.id
        assert retrieved.preferences.sync_settings.auto_post_transactions is True

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, user_repo, session):
        """save updates existing user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        # Modify and save again
        user.update_preferences(
            auto_post_transactions=True,
            default_currency="USD",
        )
        await user_repo.save(user)
        await session.flush()

        # Retrieve and check
        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found.preferences.sync_settings.auto_post_transactions is True
        assert found.preferences.sync_settings.default_currency == "USD"

    @pytest.mark.asyncio
    async def test_delete(self, user_repo, session):
        """Can delete a user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        await user_repo.delete(user.id)
        await session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_safe(self, user_repo):
        """Deleting non-existent user doesn't raise error."""
        random_id = uuid4()

        # Should not raise
        await user_repo.delete(random_id)

    @pytest.mark.asyncio
    async def test_delete_with_all_data(self, user_repo, session):
        """delete_with_all_data removes user record."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await session.flush()

        await user_repo.delete_with_all_data(user.id)
        await session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is None

    @pytest.mark.asyncio
    async def test_preserves_all_preferences(self, user_repo, session):
        """All preference fields are properly persisted and retrieved."""
        user = User.create(TEST_EMAIL)
        user.update_preferences(
            auto_post_transactions=True,
            default_currency="CHF",
            show_draft_transactions=False,
            default_date_range_days=90,
        )

        await user_repo.save(user)
        await session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)

        assert found.preferences.sync_settings.auto_post_transactions is True
        assert found.preferences.sync_settings.default_currency == "CHF"
        assert found.preferences.display_settings.show_draft_transactions is False
        assert found.preferences.display_settings.default_date_range_days == 90

    @pytest.mark.asyncio
    async def test_preserves_timestamps(self, user_repo, session):
        """Timestamps are properly persisted and retrieved."""
        user = User.create(TEST_EMAIL)
        original_created = user.created_at
        original_updated = user.updated_at

        await user_repo.save(user)
        await session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)

        # Timestamps should be preserved (may lose microsecond precision)
        assert found.created_at.date() == original_created.date()
        assert found.updated_at.date() == original_updated.date()

    @pytest.mark.asyncio
    async def test_different_emails_different_users(self, user_repo, session):
        """Different emails create different users."""
        user1 = User.create("alice@example.com")
        user2 = User.create("bob@example.com")

        await user_repo.save(user1)
        await user_repo.save(user2)
        await session.flush()

        found1 = await user_repo.find_by_email("alice@example.com")
        found2 = await user_repo.find_by_email("bob@example.com")

        assert found1 is not None
        assert found2 is not None
        assert found1.id != found2.id
