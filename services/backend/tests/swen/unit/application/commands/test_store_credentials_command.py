"""Unit tests for StoreCredentialsCommand."""

from unittest.mock import AsyncMock

import pytest

from swen.application.commands import StoreCredentialsCommand
from swen.domain.banking.exceptions import CredentialsAlreadyExistError
from swen.domain.banking.value_objects import BankCredentials


@pytest.fixture
def mock_credential_repo():
    """Mock credential repository (user-scoped)."""
    return AsyncMock()


@pytest.fixture
def command(mock_credential_repo):
    """Create command with mocked repository."""
    return StoreCredentialsCommand(mock_credential_repo)


class TestStoreCredentialsCommand:
    """Test StoreCredentialsCommand."""

    @pytest.mark.asyncio
    async def test_store_new_credentials_success(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials when none exist."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="testpin",
            endpoint="https://banking.triodos.de/fints",
        )
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-123"

        # Act
        result = await command.execute(
            credentials=credentials,
            label="Triodos Bank",
        )

        # Assert
        assert result == "cred-id-123"
        mock_credential_repo.find_by_blz.assert_called_once_with("50031000")
        mock_credential_repo.save.assert_called_once_with(
            credentials=credentials,
            label="Triodos Bank",
            tan_method=None,
            tan_medium=None,
        )

    @pytest.mark.asyncio
    async def test_store_credentials_without_label(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials without label."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="testpin",
            endpoint="https://banking.triodos.de/fints",
        )
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-456"

        # Act
        result = await command.execute(credentials=credentials)

        # Assert
        assert result == "cred-id-456"
        mock_credential_repo.save.assert_called_once_with(
            credentials=credentials,
            label=None,
            tan_method=None,
            tan_medium=None,
        )

    @pytest.mark.asyncio
    async def test_store_credentials_with_tan_settings(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials with TAN settings."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="testpin",
            endpoint="https://banking.triodos.de/fints",
        )
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-789"

        # Act
        result = await command.execute(
            credentials=credentials,
            label="Triodos Bank",
            tan_method="946",
            tan_medium="SecureGo",
        )

        # Assert
        assert result == "cred-id-789"
        mock_credential_repo.save.assert_called_once_with(
            credentials=credentials,
            label="Triodos Bank",
            tan_method="946",
            tan_medium="SecureGo",
        )

    @pytest.mark.asyncio
    async def test_raises_error_when_credentials_exist(
        self,
        command,
        mock_credential_repo,
    ):
        """Should raise error when credentials already exist for user/BLZ."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="testpin",
            endpoint="https://banking.triodos.de/fints",
        )
        # Existing credentials found (repository is user-scoped)
        existing_creds = BankCredentials.from_plain(
            blz="50031000",
            username="olduser",
            pin="oldpin",
            endpoint="https://banking.triodos.de/fints",
        )
        mock_credential_repo.find_by_blz.return_value = existing_creds

        # Act & Assert
        with pytest.raises(CredentialsAlreadyExistError):
            await command.execute(credentials=credentials)

        # Should not call save
        mock_credential_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_credentials_for_multiple_banks(
        self,
        command,
        mock_credential_repo,
    ):
        """Should allow storing credentials for different banks."""
        # Arrange
        triodos_creds = BankCredentials.from_plain(
            blz="50031000",
            username="triodos_user",
            pin="triodos_pin",
            endpoint="https://banking.triodos.de/fints",
        )
        dkb_creds = BankCredentials.from_plain(
            blz="12030000",
            username="dkb_user",
            pin="dkb_pin",
            endpoint="https://banking.dkb.de/fints",
        )

        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.side_effect = ["cred-id-1", "cred-id-2"]

        # Act
        result1 = await command.execute(triodos_creds, "Triodos")
        result2 = await command.execute(dkb_creds, "DKB")

        # Assert
        assert result1 == "cred-id-1"
        assert result2 == "cred-id-2"
        assert mock_credential_repo.save.call_count == 2
