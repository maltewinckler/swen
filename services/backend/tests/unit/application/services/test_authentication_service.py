"""Unit tests for AuthenticationService."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest

from swen_auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    JWTService,
    PasswordHashingService,
    WeakPasswordError,
)
from swen.application.services import AuthenticationService
from swen.domain.user import EmailAlreadyExistsError, User


TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "secure_password_123"


class TestAuthenticationServiceRegister:
    """Tests for user registration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.jwt_service = Mock(spec=JWTService)

        self.service = AuthenticationService(
            user_repository=self.user_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            jwt_service=self.jwt_service,
        )

    @pytest.mark.asyncio
    async def test_register_creates_user_and_returns_tokens(self):
        """Test that register creates user and returns tokens."""
        # Arrange
        self.user_repo.find_by_email.return_value = None
        self.password_service.hash.return_value = "hashed_password"
        self.jwt_service.create_access_token.return_value = "access_token"
        self.jwt_service.create_refresh_token.return_value = "refresh_token"

        # Act
        user, access_token, refresh_token = await self.service.register(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        # Assert
        assert user.email == TEST_EMAIL
        assert access_token == "access_token"
        assert refresh_token == "refresh_token"

        self.user_repo.save.assert_called_once()
        self.credential_repo.save.assert_called_once()
        self.password_service.hash.assert_called_once_with(TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_register_raises_when_email_exists(self):
        """Test that register raises EmailAlreadyExistsError for existing email."""
        # Arrange
        existing_user = User.create(TEST_EMAIL)
        self.user_repo.find_by_email.return_value = existing_user

        # Act & Assert
        with pytest.raises(EmailAlreadyExistsError):
            await self.service.register(email=TEST_EMAIL, password=TEST_PASSWORD)

        # User should not be created
        self.user_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_raises_for_weak_password(self):
        """Test that register raises WeakPasswordError for weak password."""
        # Arrange
        self.user_repo.find_by_email.return_value = None
        self.password_service.hash.side_effect = WeakPasswordError("Too short")

        # Act & Assert
        with pytest.raises(WeakPasswordError):
            await self.service.register(email=TEST_EMAIL, password="short")


class TestAuthenticationServiceLogin:
    """Tests for user login."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.jwt_service = Mock(spec=JWTService)

        self.service = AuthenticationService(
            user_repository=self.user_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            jwt_service=self.jwt_service,
        )

    @pytest.mark.asyncio
    async def test_login_returns_user_and_tokens(self):
        """Test that login returns user and tokens for valid credentials."""
        # Arrange
        user = User.create(TEST_EMAIL)
        credential = MagicMock()
        credential.password_hash = "hashed_password"

        self.user_repo.find_by_email.return_value = user
        self.credential_repo.is_account_locked.return_value = (False, None)
        self.credential_repo.find_by_user_id.return_value = credential
        self.password_service.verify.return_value = True
        self.jwt_service.create_access_token.return_value = "access_token"
        self.jwt_service.create_refresh_token.return_value = "refresh_token"

        # Act
        result_user, access_token, refresh_token = await self.service.login(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        # Assert
        assert result_user.email == TEST_EMAIL
        assert access_token == "access_token"
        assert refresh_token == "refresh_token"

        self.credential_repo.reset_failed_attempts.assert_called_once()
        self.credential_repo.update_last_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_raises_for_unknown_email(self):
        """Test that login raises InvalidCredentialsError for unknown email."""
        # Arrange
        self.user_repo.find_by_email.return_value = None

        # Act & Assert
        with pytest.raises(InvalidCredentialsError):
            await self.service.login(email="unknown@example.com", password="password")

    @pytest.mark.asyncio
    async def test_login_raises_for_wrong_password(self):
        """Test that login raises InvalidCredentialsError for wrong password."""
        # Arrange
        user = User.create(TEST_EMAIL)
        credential = MagicMock()
        credential.password_hash = "hashed_password"

        self.user_repo.find_by_email.return_value = user
        self.credential_repo.is_account_locked.return_value = (False, None)
        self.credential_repo.find_by_user_id.return_value = credential
        self.password_service.verify.return_value = False

        # Act & Assert
        with pytest.raises(InvalidCredentialsError):
            await self.service.login(email=TEST_EMAIL, password="wrong_password")

        # Failed attempts should be incremented
        self.credential_repo.increment_failed_attempts.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_raises_for_locked_account(self):
        """Test that login raises AccountLockedError for locked account."""
        # Arrange
        user = User.create(TEST_EMAIL)
        locked_until = datetime.utcnow() + timedelta(minutes=15)

        self.user_repo.find_by_email.return_value = user
        self.credential_repo.is_account_locked.return_value = (True, locked_until)

        # Act & Assert
        with pytest.raises(AccountLockedError):
            await self.service.login(email=TEST_EMAIL, password=TEST_PASSWORD)


class TestAuthenticationServiceRefreshToken:
    """Tests for token refresh."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.jwt_service = Mock(spec=JWTService)

        self.service = AuthenticationService(
            user_repository=self.user_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            jwt_service=self.jwt_service,
        )

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_tokens(self):
        """Test that refresh_token returns new tokens for valid refresh token."""
        # Arrange
        user = User.create(TEST_EMAIL)
        payload = MagicMock()
        payload.user_id = user.id
        payload.is_refresh_token.return_value = True

        self.jwt_service.verify_token.return_value = payload
        self.user_repo.find_by_id.return_value = user
        self.jwt_service.create_access_token.return_value = "new_access_token"
        self.jwt_service.create_refresh_token.return_value = "new_refresh_token"

        # Act
        access_token, refresh_token = await self.service.refresh_token(
            "valid_refresh_token"
        )

        # Assert
        assert access_token == "new_access_token"
        assert refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_raises_for_access_token(self):
        """Test that refresh_token raises for access token (not refresh)."""
        # Arrange
        payload = MagicMock()
        payload.is_refresh_token.return_value = False

        self.jwt_service.verify_token.return_value = payload

        # Act & Assert
        with pytest.raises(InvalidTokenError, match="Not a refresh token"):
            await self.service.refresh_token("access_token_not_refresh")

    @pytest.mark.asyncio
    async def test_refresh_token_raises_for_deleted_user(self):
        """Test that refresh_token raises when user no longer exists."""
        # Arrange
        payload = MagicMock()
        payload.user_id = uuid4()
        payload.is_refresh_token.return_value = True

        self.jwt_service.verify_token.return_value = payload
        self.user_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(InvalidTokenError, match="User not found"):
            await self.service.refresh_token("refresh_token")


class TestAuthenticationServiceChangePassword:
    """Tests for password change."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.jwt_service = Mock(spec=JWTService)

        self.service = AuthenticationService(
            user_repository=self.user_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            jwt_service=self.jwt_service,
        )

    @pytest.mark.asyncio
    async def test_change_password_succeeds(self):
        """Test that change_password updates password hash."""
        # Arrange
        user_id = uuid4()
        credential = MagicMock()
        credential.password_hash = "old_hash"

        self.credential_repo.find_by_user_id.return_value = credential
        self.password_service.verify.return_value = True
        self.password_service.hash.return_value = "new_hash"

        # Act
        await self.service.change_password(
            user_id=user_id,
            current_password="old_password",
            new_password="new_password_123",
        )

        # Assert
        self.password_service.verify.assert_called_once_with("old_password", "old_hash")
        self.password_service.hash.assert_called_once_with("new_password_123")
        self.credential_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_raises_for_wrong_current(self):
        """Test that change_password raises for wrong current password."""
        # Arrange
        user_id = uuid4()
        credential = MagicMock()
        credential.password_hash = "old_hash"

        self.credential_repo.find_by_user_id.return_value = credential
        self.password_service.verify.return_value = False

        # Act & Assert
        with pytest.raises(InvalidCredentialsError, match="incorrect"):
            await self.service.change_password(
                user_id=user_id,
                current_password="wrong_password",
                new_password="new_password_123",
            )

    @pytest.mark.asyncio
    async def test_change_password_raises_for_missing_credential(self):
        """Test that change_password raises when credentials not found."""
        # Arrange
        self.credential_repo.find_by_user_id.return_value = None

        # Act & Assert
        with pytest.raises(InvalidCredentialsError, match="not found"):
            await self.service.change_password(
                user_id=uuid4(),
                current_password="password",
                new_password="new_password_123",
            )

