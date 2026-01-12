"""Unit tests for PasswordHashingService."""

import pytest

from swen_auth.exceptions import WeakPasswordError
from swen_auth.services import PasswordHashingService


class TestPasswordHashingService:
    """Tests for password hashing and verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = PasswordHashingService(rounds=4)  # Low rounds for fast tests

    def test_hash_returns_bcrypt_format(self):
        """Test that hash returns a valid bcrypt hash."""
        password = "secure_password123"
        hashed = self.service.hash(password)

        # bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith("$2")
        # bcrypt hashes are ~60 characters
        assert len(hashed) >= 50

    def test_verify_correct_password(self):
        """Test that verify returns True for correct password."""
        password = "my_secret_password"
        hashed = self.service.hash(password)

        assert self.service.verify(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test that verify returns False for incorrect password."""
        password = "my_secret_password"
        hashed = self.service.hash(password)

        assert self.service.verify("wrong_password", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        """Test that verify returns False for invalid hash format."""
        assert self.service.verify("password", "not_a_valid_hash") is False
        assert self.service.verify("password", "") is False

    def test_hash_produces_different_hashes(self):
        """Test that hashing same password twice produces different hashes."""
        password = "same_password"
        hash1 = self.service.hash(password)
        hash2 = self.service.hash(password)

        # Due to random salt, hashes should differ
        assert hash1 != hash2
        # But both should verify
        assert self.service.verify(password, hash1)
        assert self.service.verify(password, hash2)


class TestPasswordValidation:
    """Tests for password strength validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = PasswordHashingService(rounds=4)

    def test_validate_empty_password_raises(self):
        """Test that empty password raises WeakPasswordError."""
        with pytest.raises(WeakPasswordError, match="cannot be empty"):
            self.service.validate_strength("")

    def test_validate_short_password_raises(self):
        """Test that password shorter than minimum raises WeakPasswordError."""
        with pytest.raises(WeakPasswordError, match="at least 8 characters"):
            self.service.validate_strength("short")

    def test_validate_too_long_password_raises(self):
        """Test that password exceeding maximum raises WeakPasswordError."""
        long_password = "a" * 129
        with pytest.raises(WeakPasswordError, match="cannot exceed 128"):
            self.service.validate_strength(long_password)

    def test_validate_valid_password_succeeds(self):
        """Test that valid password passes validation."""
        # Should not raise
        self.service.validate_strength("valid_password_123")

    def test_hash_validates_password(self):
        """Test that hash method validates password strength."""
        with pytest.raises(WeakPasswordError):
            self.service.hash("short")


class TestPasswordRehash:
    """Tests for needs_rehash functionality."""

    def test_needs_rehash_same_rounds(self):
        """Test that hash with same rounds doesn't need rehash."""
        service = PasswordHashingService(rounds=10)
        hashed = service.hash("password123")

        assert service.needs_rehash(hashed) is False

    def test_needs_rehash_different_rounds(self):
        """Test that hash with different rounds needs rehash."""
        # Create hash with rounds=10
        service10 = PasswordHashingService(rounds=10)
        hashed = service10.hash("password123")

        # Check with service that uses rounds=12
        service12 = PasswordHashingService(rounds=12)
        assert service12.needs_rehash(hashed) is True

    def test_needs_rehash_invalid_hash(self):
        """Test that invalid hash format returns True (needs rehash)."""
        service = PasswordHashingService(rounds=10)
        assert service.needs_rehash("invalid_hash") is True
        assert service.needs_rehash("") is True

