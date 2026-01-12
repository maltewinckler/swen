"""Unit tests for BankCredentials value object."""

import os
from unittest.mock import patch

import pytest
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.shared.value_objects.secure_string import SecureString
from pydantic import ValidationError


class TestBankCredentialsCreation:
    """Test BankCredentials creation and validation."""

    def test_create_with_valid_data(self):
        """Should create BankCredentials with valid data."""
        creds = BankCredentials(
            blz="12345678",
            username=SecureString("user123"),
            pin=SecureString("1234"),
            endpoint="https://bank.example.com",
        )

        assert creds.blz == "12345678"
        assert creds.username.get_value() == "user123"
        assert creds.pin.get_value() == "1234"
        assert creds.endpoint == "https://bank.example.com"

    def test_from_plain_factory(self):
        """from_plain() should wrap strings in SecureString."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="user123",
            pin="1234",
            endpoint="https://bank.example.com",
        )

        assert isinstance(creds.username, SecureString)
        assert isinstance(creds.pin, SecureString)
        assert creds.username.get_value() == "user123"
        assert creds.pin.get_value() == "1234"


class TestBankCredentialsValidation:
    """Test validation rules."""

    def test_reject_short_blz(self):
        """BLZ must be exactly 8 digits."""
        with pytest.raises(
            ValueError,
            match=r"(at least 8 characters|exactly 8 digits)",
        ):
            BankCredentials.from_plain(
                blz="123",  # Too short
                username="user",
                pin="1234",
                endpoint="https://bank.example.com",
            )

    def test_reject_long_blz(self):
        """BLZ must be exactly 8 digits."""
        with pytest.raises(
            ValueError,
            match=r"(at most 8 characters|exactly 8 digits)",
        ):
            BankCredentials.from_plain(
                blz="123456789",  # Too long
                username="user",
                pin="1234",
                endpoint="https://bank.example.com",
            )

    def test_reject_non_numeric_blz(self):
        """BLZ must contain only digits."""
        with pytest.raises(ValueError, match="only digits"):
            BankCredentials.from_plain(
                blz="1234567X",  # Contains letter
                username="user",
                pin="1234",
                endpoint="https://bank.example.com",
            )

    def test_reject_empty_endpoint(self):
        """Endpoint is required."""
        with pytest.raises(
            ValueError,
            match=r"(at least 1 character|required)",
        ):
            BankCredentials.from_plain(
                blz="12345678",
                username="user",
                pin="1234",
                endpoint="",  # Empty
            )

    def test_reject_non_securestring_username(self):
        """Plain strings should be automatically converted to SecureString."""
        # Pydantic now automatically converts strings to SecureString
        creds = BankCredentials(
            blz="12345678",
            username="plain_string",  # type: ignore[arg-type]  # Automatically converted
            pin=SecureString("1234"),
            endpoint="https://bank.example.com",
        )

        # Verify it was converted to SecureString
        assert isinstance(creds.username, SecureString)
        assert creds.username.get_value() == "plain_string"

    def test_reject_non_securestring_pin(self):
        """Plain strings should be automatically converted to SecureString."""
        # Pydantic now automatically converts strings to SecureString
        creds = BankCredentials(
            blz="12345678",
            username=SecureString("user"),
            pin="plain_string",  # type: ignore[arg-type]  # Automatically converted
            endpoint="https://bank.example.com",
        )

        # Verify it was converted to SecureString
        assert isinstance(creds.pin, SecureString)
        assert creds.pin.get_value() == "plain_string"

    def test_reject_empty_username(self):
        """Empty username should be rejected."""
        with pytest.raises(ValidationError, match="SecureString cannot be empty"):
            BankCredentials(
                blz="12345678",
                username="",  # type: ignore[arg-type]  # Empty string
                pin=SecureString("1234"),
                endpoint="https://bank.example.com",
            )

    def test_reject_empty_pin(self):
        """Empty PIN should be rejected."""
        with pytest.raises(ValidationError, match="SecureString cannot be empty"):
            BankCredentials(
                blz="12345678",
                username=SecureString("user"),
                pin="",  # type: ignore[arg-type]  # Empty string
                endpoint="https://bank.example.com",
            )


class TestBankCredentialsSecurity:
    """Test that credentials are masked in output."""

    def test_str_masks_credentials(self):
        """__str__ should mask username and PIN."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="secret_user",
            pin="secret_pin",
            endpoint="https://bank.example.com",
        )

        str_output = str(creds)

        assert "secret_user" not in str_output
        assert "secret_pin" not in str_output
        assert "12345678" in str_output  # BLZ is not secret
        assert "https://bank.example.com" in str_output  # Endpoint is not secret

    def test_repr_masks_credentials(self):
        """__repr__ should mask username and PIN."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="secret_user",
            pin="secret_pin",
            endpoint="https://bank.example.com",
        )

        repr_output = repr(creds)

        assert "secret_user" not in repr_output
        assert "secret_pin" not in repr_output
        assert "*****" in repr_output
        assert "12345678" in repr_output

    def test_format_masks_credentials(self):
        """String formatting should mask credentials."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="secret_user",
            pin="secret_pin",
            endpoint="https://bank.example.com",
        )

        formatted = f"Credentials: {creds}"

        assert "secret_user" not in formatted
        assert "secret_pin" not in formatted


class TestBankCredentialsImmutability:
    """Test that BankCredentials is immutable."""

    def test_frozen_dataclass(self):
        """Should not allow attribute modification."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="user",
            pin="1234",
            endpoint="https://bank.example.com",
        )

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: PT011, B017
            creds.blz = "87654321"

    def test_credentials_remain_constant(self):
        """Credentials should remain constant after creation."""
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="user",
            pin="1234",
            endpoint="https://bank.example.com",
        )

        # Values should remain unchanged
        assert creds.blz == "12345678"
        assert creds.username.get_value() == "user"
        assert creds.pin.get_value() == "1234"


class TestBankCredentialsFromEnv:
    """Test from_env factory method."""

    def test_from_env_with_valid_variables(self):
        """Should load from environment variables."""
        env_vars = {
            "FINTS_USERNAME": "test_user",
            "FINTS_PIN": "test_pin",
        }

        with patch.dict(os.environ, env_vars):
            creds = BankCredentials.from_env(
                blz="12345678",
                endpoint="https://bank.example.com",
            )

            assert creds.username.get_value() == "test_user"
            assert creds.pin.get_value() == "test_pin"

    def test_from_env_with_missing_username(self):
        """Should raise error if FINTS_USERNAME not set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(
                ValueError,
                match="not found",
            ),
        ):
            BankCredentials.from_env(
                blz="12345678",
                endpoint="https://bank.example.com",
            )

    def test_from_env_with_missing_pin(self):
        """Should raise error if FINTS_PIN not set."""
        with (
            patch.dict(os.environ, {"FINTS_USERNAME": "user"}, clear=True),
            pytest.raises(
                ValueError,
                match="not found",
            ),
        ):
            BankCredentials.from_env(
                blz="12345678",
                endpoint="https://bank.example.com",
            )


class TestBankCredentialsRealWorld:
    """Test with real-world scenarios."""

    def test_triodos_bank_credentials(self):
        """Test with actual Triodos Bank BLZ."""
        creds = BankCredentials.from_plain(
            blz="50031000",  # Triodos Bank
            username="test_user",
            pin="test_pin",
            endpoint="https://banking.triodos.de/fints",
        )

        assert creds.blz == "50031000"
        assert creds.endpoint == "https://banking.triodos.de/fints"

    def test_long_endpoint_url(self):
        """Should handle long endpoint URLs."""
        long_url = "https://banking.example.com/fints/fints-server/v1/PinTanServlet"
        creds = BankCredentials.from_plain(
            blz="12345678",
            username="user",
            pin="1234",
            endpoint=long_url,
        )

        assert creds.endpoint == long_url
