"""Unit tests for admin commands."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from swen.application.commands.admin import (
    CreateUserCommand,
    DeleteUserCommand,
    UpdateUserRoleCommand,
)
from swen.domain.user import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    EmailAlreadyExistsError,
    User,
    UserNotFoundError,
    UserRole,
)
from swen_auth.services import PasswordHashingService


TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "secure_password_123"


class TestCreateUserCommand:
    """Tests for CreateUserCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.password_service.hash.return_value = "hashed_password"

        self.command = CreateUserCommand(
            user_repository=self.user_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Successfully creates a new user."""
        self.user_repo.find_by_email.return_value = None

        user = await self.command.execute(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        assert user.email == TEST_EMAIL
        assert user.role == UserRole.USER
        self.user_repo.save.assert_called_once()
        self.credential_repo.save.assert_called_once()
        self.password_service.hash.assert_called_once_with(TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_create_admin_user(self):
        """Can create an admin user."""
        self.user_repo.find_by_email.return_value = None

        user = await self.command.execute(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            role=UserRole.ADMIN,
        )

        assert user.email == TEST_EMAIL
        assert user.role == UserRole.ADMIN
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises(self):
        """Raises EmailAlreadyExistsError for duplicate email."""
        existing_user = User.create(TEST_EMAIL)
        self.user_repo.find_by_email.return_value = existing_user

        with pytest.raises(EmailAlreadyExistsError):
            await self.command.execute(
                email=TEST_EMAIL,
                password=TEST_PASSWORD,
            )

        self.user_repo.save.assert_not_called()
        self.credential_repo.save.assert_not_called()


class TestDeleteUserCommand:
    """Tests for DeleteUserCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.command = DeleteUserCommand(user_repository=self.user_repo)

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Successfully deletes a user."""
        user_id = uuid4()
        admin_id = uuid4()
        user = User.create(TEST_EMAIL)

        self.user_repo.find_by_id.return_value = user

        await self.command.execute(
            user_id=user_id,
            requesting_admin_id=admin_id,
        )

        self.user_repo.delete_with_all_data.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_delete_self_raises(self):
        """Raises CannotDeleteSelfError when deleting self."""
        admin_id = uuid4()

        with pytest.raises(CannotDeleteSelfError):
            await self.command.execute(
                user_id=admin_id,
                requesting_admin_id=admin_id,
            )

        self.user_repo.find_by_id.assert_not_called()
        self.user_repo.delete_with_all_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_raises(self):
        """Raises UserNotFoundError for non-existent user."""
        user_id = uuid4()
        admin_id = uuid4()
        self.user_repo.find_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await self.command.execute(
                user_id=user_id,
                requesting_admin_id=admin_id,
            )

        self.user_repo.delete_with_all_data.assert_not_called()


class TestUpdateUserRoleCommand:
    """Tests for UpdateUserRoleCommand."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.command = UpdateUserRoleCommand(user_repository=self.user_repo)

    @pytest.mark.asyncio
    async def test_promote_to_admin(self):
        """Successfully promotes user to admin."""
        user_id = uuid4()
        admin_id = uuid4()
        user = User.create(TEST_EMAIL)
        self.user_repo.find_by_id.return_value = user

        result = await self.command.execute(
            user_id=user_id,
            new_role=UserRole.ADMIN,
            requesting_admin_id=admin_id,
        )

        assert result.role == UserRole.ADMIN
        assert result.is_admin is True
        self.user_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_demote_to_user(self):
        """Successfully demotes admin to user."""
        user_id = uuid4()
        admin_id = uuid4()
        user = User.create(TEST_EMAIL, role=UserRole.ADMIN)
        self.user_repo.find_by_id.return_value = user

        result = await self.command.execute(
            user_id=user_id,
            new_role=UserRole.USER,
            requesting_admin_id=admin_id,
        )

        assert result.role == UserRole.USER
        assert result.is_admin is False
        self.user_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_demote_self_raises(self):
        """Raises CannotDemoteSelfError when demoting self."""
        admin_id = uuid4()

        with pytest.raises(CannotDemoteSelfError):
            await self.command.execute(
                user_id=admin_id,
                new_role=UserRole.USER,
                requesting_admin_id=admin_id,
            )

        self.user_repo.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_promote_self_allowed(self):
        """Self-promotion (keeping admin role) is allowed."""
        admin_id = uuid4()
        user = User.create(TEST_EMAIL, role=UserRole.ADMIN)
        self.user_repo.find_by_id.return_value = user

        result = await self.command.execute(
            user_id=admin_id,
            new_role=UserRole.ADMIN,
            requesting_admin_id=admin_id,
        )

        # Should not raise - setting self to admin (same role) is fine
        assert result.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_raises(self):
        """Raises UserNotFoundError for non-existent user."""
        user_id = uuid4()
        admin_id = uuid4()
        self.user_repo.find_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await self.command.execute(
                user_id=user_id,
                new_role=UserRole.ADMIN,
                requesting_admin_id=admin_id,
            )

        self.user_repo.save.assert_not_called()
