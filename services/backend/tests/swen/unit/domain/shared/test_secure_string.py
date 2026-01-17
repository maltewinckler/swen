"""Unit tests for SecureString value object."""

import os
from unittest.mock import patch

import pytest

from swen.domain.shared.value_objects.secure_string import SecureString


class TestSecureStringCreation:
    """Test SecureString creation and validation."""

    def test_create_with_valid_string(self):
        """Should create SecureString with valid string."""
        secure = SecureString("my_secret")
        assert secure.get_value() == "my_secret"

    def test_reject_empty_string(self):
        """Should reject empty string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SecureString("")

    def test_reject_non_string(self):
        """Should reject non-string values."""
        with pytest.raises(TypeError, match="must be a string"):
            SecureString(123)  # type: ignore[arg-type]

    def test_reject_none(self):
        """Should reject None value."""
        with pytest.raises(TypeError):
            SecureString(None)  # type: ignore[arg-type]


class TestSecureStringMasking:
    """Test that SecureString masks sensitive data."""

    def test_str_returns_masked(self):
        """__str__ should return masked value."""
        secure = SecureString("super_secret_password")
        assert str(secure) == "*****"
        assert "super_secret" not in str(secure)

    def test_repr_returns_masked(self):
        """__repr__ should return masked value."""
        secure = SecureString("super_secret_password")
        assert repr(secure) == "SecureString(*****)"
        assert "super_secret" not in repr(secure)

    def test_format_returns_masked(self):
        """String formatting should return masked value."""
        secure = SecureString("secret123")
        formatted = f"Password: {secure}"
        assert formatted == "Password: *****"
        assert "secret123" not in formatted


class TestSecureStringAccess:
    """Test explicit value access."""

    def test_get_value_returns_actual_value(self):
        """get_value() should return the actual secret."""
        secret = "my_actual_secret"  # NOQA: S105
        secure = SecureString(secret)
        assert secure.get_value() == secret

    def test_get_value_is_only_way_to_access(self):
        """Verify there's no other way to access the value accidentally."""
        secure = SecureString("secret")

        # These should all be masked
        assert "secret" not in str(secure)
        assert "secret" not in repr(secure)
        assert "secret" not in f"{secure}"

        # Only get_value() reveals it
        assert secure.get_value() == "secret"


class TestSecureStringComparison:
    """Test SecureString equality and hashing."""

    def test_equality_with_same_value(self):
        """Two SecureStrings with same value should be equal."""
        secure1 = SecureString("password")
        secure2 = SecureString("password")
        assert secure1 == secure2

    def test_inequality_with_different_value(self):
        """Two SecureStrings with different values should not be equal."""
        secure1 = SecureString("password1")
        secure2 = SecureString("password2")
        assert secure1 != secure2

    def test_inequality_with_plain_string(self):
        """SecureString should not equal plain string."""
        secure = SecureString("password")
        assert secure != "password"

    def test_hashable(self):
        """SecureString should be hashable (for use in sets/dicts)."""
        secure1 = SecureString("password")
        secure2 = SecureString("password")

        # Should work in set
        secure_set = {secure1, secure2}
        assert len(secure_set) == 1  # Same value, so only one item

    def test_hash_equality(self):
        """Equal SecureStrings should have equal hashes."""
        secure1 = SecureString("password")
        secure2 = SecureString("password")
        assert hash(secure1) == hash(secure2)


class TestSecureStringHelpers:
    """Test helper methods."""

    def test_len_returns_length(self):
        """len() should return length without exposing value."""
        secure = SecureString("12345")
        assert len(secure) == 5

    def test_matches_with_plain_string(self):
        """matches() should compare with plain string."""
        secure = SecureString("password")
        assert secure.matches("password")
        assert not secure.matches("wrong")

    def test_is_empty(self):
        """is_empty() should always be False (validated on creation)."""
        secure = SecureString("value")
        assert not secure.is_empty()


class TestSecureStringFromEnv:
    """Test factory method from environment variables."""

    def test_from_env_with_existing_var(self):
        """Should create SecureString from environment variable."""
        with patch.dict(os.environ, {"TEST_SECRET": "secret_value"}):
            secure = SecureString.from_env("TEST_SECRET")
            assert secure.get_value() == "secret_value"

    def test_from_env_with_missing_var(self):
        """Should raise ValueError if environment variable not found."""
        with patch.dict(os.environ, {}, clear=True):  # NOQA: SIM117
            with pytest.raises(ValueError, match="not found"):
                SecureString.from_env("NONEXISTENT_VAR")

    def test_from_env_with_empty_var(self):
        """Should raise ValueError if environment variable is empty."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):  # NOQA: SIM117
            with pytest.raises(ValueError, match="cannot be empty"):
                SecureString.from_env("EMPTY_VAR")


class TestSecureStringImmutability:
    """Test that SecureString is immutable."""

    def test_frozen_dataclass(self):
        """Should not allow attribute modification."""
        secure = SecureString("secret")

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: PT011, B017
            secure._value = "new_value"  # type: ignore[misc]

    def test_value_remains_constant(self):
        """Value should remain constant after creation."""
        original = "original_secret"
        secure = SecureString(original)

        # Even if we modify the original string (which we can't in Python),
        # the SecureString should keep its value
        assert secure.get_value() == original
