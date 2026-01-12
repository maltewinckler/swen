"""Unit tests for JWTService."""

from datetime import timedelta
from uuid import uuid4

import pytest

from swen_auth.exceptions import InvalidTokenError
from swen_auth.services import JWTService


class TestJWTServiceInit:
    """Tests for JWTService initialization."""

    def test_init_with_valid_secret(self):
        """Test that service initializes with valid secret."""
        service = JWTService(secret_key="test-secret-key")
        assert service is not None

    def test_init_with_empty_secret_raises(self):
        """Test that empty secret raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            JWTService(secret_key="")

    def test_init_with_custom_expiry(self):
        """Test that custom expiry times are accepted."""
        service = JWTService(
            secret_key="test-secret",
            access_token_expire_hours=1,
            refresh_token_expire_days=7,
        )
        assert service is not None


class TestAccessTokens:
    """Tests for access token creation and verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = JWTService(secret_key="test-secret-key-12345")
        self.user_id = uuid4()
        self.email = "test@example.com"

    def test_create_access_token(self):
        """Test that access token is created successfully."""
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_access_token(self):
        """Test that valid access token is verified correctly."""
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )

        payload = self.service.verify_token(token)

        assert payload.user_id == self.user_id
        assert payload.email == self.email
        assert payload.token_type == "access"
        assert payload.is_access_token()
        assert not payload.is_refresh_token()

    def test_verify_expired_token_raises(self):
        """Test that expired token raises InvalidTokenError."""
        # Create token that expires immediately
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(InvalidTokenError, match="expired"):
            self.service.verify_token(token)

    def test_verify_invalid_token_raises(self):
        """Test that invalid token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            self.service.verify_token("invalid.token.string")

    def test_verify_tampered_token_raises(self):
        """Test that tampered token raises InvalidTokenError."""
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )

        # Tamper with the token
        tampered = token[:-5] + "xxxxx"

        with pytest.raises(InvalidTokenError):
            self.service.verify_token(tampered)

    def test_verify_wrong_secret_raises(self):
        """Test that token from different secret raises InvalidTokenError."""
        other_service = JWTService(secret_key="different-secret")
        token = other_service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )

        with pytest.raises(InvalidTokenError):
            self.service.verify_token(token)


class TestRefreshTokens:
    """Tests for refresh token creation and verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = JWTService(secret_key="test-secret-key-12345")
        self.user_id = uuid4()
        self.email = "test@example.com"

    def test_create_refresh_token(self):
        """Test that refresh token is created successfully."""
        token = self.service.create_refresh_token(
            user_id=self.user_id,
            email=self.email,
        )

        assert token is not None
        assert isinstance(token, str)

    def test_verify_refresh_token(self):
        """Test that refresh token is verified with correct type."""
        token = self.service.create_refresh_token(
            user_id=self.user_id,
            email=self.email,
        )

        payload = self.service.verify_token(token)

        assert payload.user_id == self.user_id
        assert payload.email == self.email
        assert payload.token_type == "refresh"
        assert payload.is_refresh_token()
        assert not payload.is_access_token()

    def test_access_and_refresh_tokens_differ(self):
        """Test that access and refresh tokens are different."""
        access = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )
        refresh = self.service.create_refresh_token(
            user_id=self.user_id,
            email=self.email,
        )

        assert access != refresh


class TestTokenPayload:
    """Tests for TokenPayload methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = JWTService(
            secret_key="test-secret",
            access_token_expire_hours=1,
        )
        self.user_id = uuid4()
        self.email = "test@example.com"

    def test_is_expired_returns_false_for_valid_token(self):
        """Test that is_expired returns False for valid token."""
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )
        payload = self.service.verify_token(token)

        assert payload.is_expired() is False

    def test_payload_contains_expiry(self):
        """Test that payload contains expiry timestamp."""
        token = self.service.create_access_token(
            user_id=self.user_id,
            email=self.email,
        )
        payload = self.service.verify_token(token)

        assert payload.exp is not None

