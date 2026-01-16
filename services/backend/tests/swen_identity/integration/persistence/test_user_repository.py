"""Integration tests for UserRepository with Testcontainers PostgreSQL."""

from uuid import UUID, uuid4

import pytest

from swen_identity.domain.user import User, UserRole
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserRepositorySQLAlchemy,
)

TEST_EMAIL = "test@example.com"


@pytest.fixture
def user_repo(db_session):
    """Create UserRepository instance with the test session."""
    return UserRepositorySQLAlchemy(db_session)


@pytest.mark.integration
class TestUserRepositorySQLAlchemy:
    """Integration tests for UserRepositorySQLAlchemy."""

    @pytest.mark.asyncio
    async def test_save_and_find_by_id(self, user_repo, db_session):
        """Can save and retrieve a user by ID."""
        user = User.create(TEST_EMAIL)

        await user_repo.save(user)
        await db_session.flush()

        found = await user_repo.find_by_id(user.id)

        assert found is not None
        assert found.id == user.id
        assert isinstance(found.id, UUID)
        assert found.email == TEST_EMAIL
        assert found.role == UserRole.USER

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, user_repo):
        """Returns None for non-existent user."""
        random_id = uuid4()

        found = await user_repo.find_by_id(random_id)

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email(self, user_repo, db_session):
        """Can find user by email."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)

        assert found is not None
        assert found.email == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_find_by_email_case_insensitive(self, user_repo, db_session):
        """find_by_email is case insensitive."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        found = await user_repo.find_by_email("TEST@EXAMPLE.COM")

        assert found is not None
        assert found.email == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(self, user_repo):
        """Returns None for non-existent email."""
        found = await user_repo.find_by_email("nonexistent@example.com")

        assert found is None

    @pytest.mark.asyncio
    async def test_exists_by_email(self, user_repo, db_session):
        """exists_by_email returns True for existing user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        exists = await user_repo.exists_by_email(TEST_EMAIL)

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_email_not_found(self, user_repo):
        """exists_by_email returns False for non-existent user."""
        exists = await user_repo.exists_by_email("nonexistent@example.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_get_or_create_by_email_creates(self, user_repo, db_session):
        """get_or_create_by_email creates user if not exists."""
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        await db_session.flush()

        assert user.email == TEST_EMAIL
        assert isinstance(user.id, UUID)
        assert user.role == UserRole.USER

        # Should be persisted
        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is not None
        assert found.id == user.id  # Same ID

    @pytest.mark.asyncio
    async def test_get_or_create_by_email_returns_existing(self, user_repo, db_session):
        """get_or_create_by_email returns existing user."""
        # Create user first
        original = await user_repo.get_or_create_by_email(TEST_EMAIL)
        original.promote_to_admin()
        await user_repo.save(original)
        await db_session.flush()

        # Get again
        retrieved = await user_repo.get_or_create_by_email(TEST_EMAIL)

        assert retrieved.id == original.id
        assert retrieved.is_admin is True

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, user_repo, db_session):
        """save updates existing user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        # Modify and save again
        user.promote_to_admin()
        await user_repo.save(user)
        await db_session.flush()

        # Retrieve and check
        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found.is_admin is True

    @pytest.mark.asyncio
    async def test_delete(self, user_repo, db_session):
        """Can delete a user."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        await user_repo.delete(user.id)
        await db_session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_safe(self, user_repo):
        """Deleting non-existent user doesn't raise error."""
        random_id = uuid4()

        # Should not raise
        await user_repo.delete(random_id)

    @pytest.mark.asyncio
    async def test_delete_with_all_data(self, user_repo, db_session):
        """delete_with_all_data removes user record."""
        user = User.create(TEST_EMAIL)
        await user_repo.save(user)
        await db_session.flush()

        await user_repo.delete_with_all_data(user.id)
        await db_session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found is None

    @pytest.mark.asyncio
    async def test_preserves_timestamps(self, user_repo, db_session):
        """Timestamps are properly persisted and retrieved."""
        user = User.create(TEST_EMAIL)
        original_created = user.created_at
        original_updated = user.updated_at

        await user_repo.save(user)
        await db_session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)

        # Timestamps should be preserved (may lose microsecond precision)
        assert found.created_at.date() == original_created.date()
        assert found.updated_at.date() == original_updated.date()

    @pytest.mark.asyncio
    async def test_different_emails_different_users(self, user_repo, db_session):
        """Different emails create different users."""
        user1 = User.create("alice@example.com")
        user2 = User.create("bob@example.com")

        await user_repo.save(user1)
        await user_repo.save(user2)
        await db_session.flush()

        found1 = await user_repo.find_by_email("alice@example.com")
        found2 = await user_repo.find_by_email("bob@example.com")

        assert found1 is not None
        assert found2 is not None
        assert found1.id != found2.id

    @pytest.mark.asyncio
    async def test_promote_and_demote_user(self, user_repo, db_session):
        """Can promote and demote user roles."""
        user = User.create(TEST_EMAIL)
        assert user.role == UserRole.USER

        user.promote_to_admin()
        await user_repo.save(user)
        await db_session.flush()

        found = await user_repo.find_by_email(TEST_EMAIL)
        assert found.role == UserRole.ADMIN
        assert found.is_admin is True

        found.demote_to_user()
        await user_repo.save(found)
        await db_session.flush()

        found2 = await user_repo.find_by_email(TEST_EMAIL)
        assert found2.role == UserRole.USER
        assert found2.is_admin is False
