"""Unit tests for PasswordResetService."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from swen.domain.shared.time import utc_now
from swen_identity import (
    InvalidResetTokenError,
    PasswordHashingService,
    User,
)
from swen_identity.application.services import PasswordResetService
from swen_identity.infrastructure.email import EmailService
from swen_identity.repositories import PasswordResetTokenData

TEST_EMAIL = "test@example.com"
TEST_TOKEN = "test-token-abc123"
TEST_NEW_PASSWORD = "new_secure_password_123"
FRONTEND_URL = "https://example.com"


class TestPasswordResetServiceRequestReset:
    """Tests for request_reset."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.token_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.email_service = Mock(spec=EmailService)

        self.service = PasswordResetService(
            user_repository=self.user_repo,
            token_repository=self.token_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            email_service=self.email_service,
            frontend_base_url=FRONTEND_URL,
        )

    @pytest.mark.asyncio
    async def test_request_reset_success(self):
        """Successfully requests a password reset."""
        user = User.create(TEST_EMAIL)
        self.user_repo.find_by_email.return_value = user
        self.token_repo.count_recent_for_user.return_value = 0

        await self.service.request_reset(TEST_EMAIL)

        self.token_repo.invalidate_all_for_user.assert_called_once_with(user.id)
        self.token_repo.create.assert_called_once()
        self.email_service.send_password_reset_email.assert_called_once()

        # Verify reset link contains frontend URL
        call_args = self.email_service.send_password_reset_email.call_args
        assert call_args[0][0] == TEST_EMAIL  # to_email
        assert FRONTEND_URL in call_args[0][1]  # reset_link

    @pytest.mark.asyncio
    async def test_request_reset_unknown_email_silent(self):
        """Unknown email silently fails (no email enumeration)."""
        self.user_repo.find_by_email.return_value = None

        await self.service.request_reset("unknown@example.com")

        self.token_repo.create.assert_not_called()
        self.email_service.send_password_reset_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_reset_rate_limited(self):
        """Rate limited requests fail silently."""
        user = User.create(TEST_EMAIL)
        self.user_repo.find_by_email.return_value = user
        self.token_repo.count_recent_for_user.return_value = 3  # At limit

        await self.service.request_reset(TEST_EMAIL)

        # Should not create token or send email
        self.token_repo.create.assert_not_called()
        self.email_service.send_password_reset_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_reset_email_failure_continues(self):
        """Token is still created even if email fails."""
        user = User.create(TEST_EMAIL)
        self.user_repo.find_by_email.return_value = user
        self.token_repo.count_recent_for_user.return_value = 0
        self.email_service.send_password_reset_email.side_effect = Exception(
            "SMTP error"
        )

        # Should not raise
        await self.service.request_reset(TEST_EMAIL)

        # Token should still be created
        self.token_repo.create.assert_called_once()


class TestPasswordResetServiceResetPassword:
    """Tests for reset_password."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_repo = AsyncMock()
        self.token_repo = AsyncMock()
        self.credential_repo = AsyncMock()
        self.password_service = Mock(spec=PasswordHashingService)
        self.password_service.hash.return_value = "new_hash"
        self.email_service = Mock(spec=EmailService)

        self.service = PasswordResetService(
            user_repository=self.user_repo,
            token_repository=self.token_repo,
            credential_repository=self.credential_repo,
            password_service=self.password_service,
            email_service=self.email_service,
            frontend_base_url=FRONTEND_URL,
        )

    def _create_valid_token_data(self, user_id=None):
        """Create a valid token data object."""
        return PasswordResetTokenData(
            id=uuid4(),
            user_id=user_id or uuid4(),
            token_hash="hashed_token",
            expires_at=utc_now() + timedelta(hours=1),
            used_at=None,
            created_at=utc_now(),
        )

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Successfully resets password."""
        token_data = self._create_valid_token_data()
        self.token_repo.find_valid_by_hash.return_value = token_data

        await self.service.reset_password(TEST_TOKEN, TEST_NEW_PASSWORD)

        self.password_service.hash.assert_called_once_with(TEST_NEW_PASSWORD)
        self.credential_repo.save.assert_called_once_with(
            user_id=token_data.user_id,
            password_hash="new_hash",
        )
        self.token_repo.mark_used.assert_called_once_with(token_data.id)

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self):
        """Raises InvalidResetTokenError for invalid token."""
        self.token_repo.find_valid_by_hash.return_value = None

        with pytest.raises(InvalidResetTokenError):
            await self.service.reset_password(TEST_TOKEN, TEST_NEW_PASSWORD)

        self.credential_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self):
        """Raises InvalidResetTokenError for expired token."""
        token_data = PasswordResetTokenData(
            id=uuid4(),
            user_id=uuid4(),
            token_hash="hashed_token",
            expires_at=utc_now() - timedelta(hours=1),  # Expired
            used_at=None,
            created_at=utc_now() - timedelta(hours=2),
        )
        self.token_repo.find_valid_by_hash.return_value = token_data

        with pytest.raises(InvalidResetTokenError):
            await self.service.reset_password(TEST_TOKEN, TEST_NEW_PASSWORD)

        self.credential_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_already_used_token(self):
        """Raises InvalidResetTokenError for already used token."""
        token_data = PasswordResetTokenData(
            id=uuid4(),
            user_id=uuid4(),
            token_hash="hashed_token",
            expires_at=utc_now() + timedelta(hours=1),
            used_at=utc_now() - timedelta(minutes=30),  # Already used
            created_at=utc_now() - timedelta(hours=1),
        )
        self.token_repo.find_valid_by_hash.return_value = token_data

        with pytest.raises(InvalidResetTokenError):
            await self.service.reset_password(TEST_TOKEN, TEST_NEW_PASSWORD)

        self.credential_repo.save.assert_not_called()
