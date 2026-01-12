"""Unit tests for BankConnectionCommand with credential loading."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from swen.application.commands import BankConnectionCommand
from swen.domain.banking.value_objects import BankAccount, BankCredentials
from swen.domain.shared.value_objects.secure_string import SecureString


TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_credentials(blz="50031000") -> BankCredentials:
    return BankCredentials(
        blz=blz,
        username=SecureString("user"),
        pin=SecureString("123456"),
        endpoint="https://fints.example.com/fints",
    )


def _make_bank_account(iban="DE89370400440532013000") -> BankAccount:
    return BankAccount(
        iban=iban,
        account_number="532013000",
        blz="37040044",
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
        balance=Decimal("1000.00"),
    )


@pytest.fixture
def mock_adapter():
    """Mock bank adapter."""
    adapter = AsyncMock()
    adapter.is_connected = Mock(return_value=False)
    adapter.set_tan_callback = AsyncMock()
    adapter.set_tan_method = Mock()
    adapter.set_tan_medium = Mock()
    adapter.connect = AsyncMock()
    adapter.fetch_accounts = AsyncMock(return_value=[])
    adapter.disconnect = AsyncMock()
    return adapter


@pytest.fixture
def mock_import_service():
    """Mock import service."""
    return AsyncMock()


@pytest.fixture
def mock_credential_repo():
    """Mock credential repository (user-scoped, no user_id params)."""
    repo = AsyncMock()
    repo.find_by_blz = AsyncMock()  # User-scoped, so no user_id param
    repo.update_last_used = AsyncMock()
    repo.get_tan_settings = AsyncMock(return_value=(None, None))
    return repo


@pytest.fixture
def command_with_credential_repo(
    mock_adapter,
    mock_import_service,
    mock_credential_repo,
):
    """Create command with credential repository."""
    return BankConnectionCommand(
        bank_adapter=mock_adapter,
        import_service=mock_import_service,
        credential_repo=mock_credential_repo,
    )


class TestBankConnectionCommandWithCredentialLoading:
    """Test credential loading functionality.

    Note: The credential repository is now user-scoped, so user_id is not
    passed to repository methods - it's implicit in the repository's context.
    """

    @pytest.mark.asyncio
    async def test_loads_credentials_from_storage_when_blz_provided(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
        mock_import_service,
    ):
        """Should load credentials from repository when blz provided."""
        # Arrange
        blz = "50031000"
        stored_credentials = _make_credentials(blz)
        mock_credential_repo.find_by_blz.return_value = stored_credentials

        bank_account = _make_bank_account()
        mock_adapter.fetch_accounts.return_value = [bank_account]
        mock_import_service.import_bank_account.return_value = (
            Mock(id=uuid4()),
            Mock(),
        )

        # Act - no user_id needed, repository is user-scoped
        result = await command_with_credential_repo.execute(blz=blz)

        # Assert
        assert result.success is True
        # Repository is user-scoped, so only blz is passed
        mock_credential_repo.find_by_blz.assert_called_once_with(blz)
        mock_adapter.connect.assert_called_once_with(stored_credentials)

    @pytest.mark.asyncio
    async def test_updates_last_used_after_connection_with_stored_credentials(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
        mock_import_service,
    ):
        """Should update last_used timestamp when using stored credentials."""
        # Arrange
        blz = "50031000"
        stored_credentials = _make_credentials(blz)
        mock_credential_repo.find_by_blz.return_value = stored_credentials

        bank_account = _make_bank_account()
        mock_adapter.fetch_accounts.return_value = [bank_account]
        mock_import_service.import_bank_account.return_value = (
            Mock(id=uuid4()),
            Mock(),
        )

        # Act
        result = await command_with_credential_repo.execute(blz=blz)

        # Assert
        assert result.success is True
        # Repository is user-scoped, so only blz is passed
        mock_credential_repo.update_last_used.assert_called_once_with(blz)

    @pytest.mark.asyncio
    async def test_does_not_update_last_used_when_credentials_provided_directly(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
        mock_import_service,
    ):
        """Should not update last_used when credentials provided directly."""
        # Arrange
        credentials = _make_credentials()
        bank_account = _make_bank_account()
        mock_adapter.fetch_accounts.return_value = [bank_account]
        mock_import_service.import_bank_account.return_value = (
            Mock(id=uuid4()),
            Mock(),
        )

        # Act
        result = await command_with_credential_repo.execute(credentials=credentials)

        # Assert
        assert result.success is True
        mock_credential_repo.find_by_blz.assert_not_called()
        mock_credential_repo.update_last_used.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_nothing_provided(
        self,
        command_with_credential_repo,
    ):
        """Should raise error when neither credentials nor blz provided."""
        # Act
        result = await command_with_credential_repo.execute()

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "blz is required" in result.error_message

    @pytest.mark.asyncio
    async def test_raises_error_when_stored_credentials_not_found(
        self,
        command_with_credential_repo,
        mock_credential_repo,
    ):
        """Should return error result when stored credentials don't exist."""
        # Arrange
        blz = "50031000"
        mock_credential_repo.find_by_blz.return_value = None

        # Act
        result = await command_with_credential_repo.execute(blz=blz)

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "No stored credentials found" in result.error_message

    @pytest.mark.asyncio
    async def test_raises_error_when_credential_repo_not_provided(
        self,
        mock_adapter,
        mock_import_service,
    ):
        """Should return error result when trying to load credentials without repo."""
        # Arrange - command without credential_repo
        command = BankConnectionCommand(
            bank_adapter=mock_adapter,
            import_service=mock_import_service,
            credential_repo=None,  # No credential repository
        )

        # Act
        result = await command.execute(blz="50031000")

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "credential_repo not provided" in result.error_message

    @pytest.mark.asyncio
    async def test_prefers_provided_credentials_over_loading(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
        mock_import_service,
    ):
        """Should use provided credentials even when blz given."""
        # Arrange
        provided_credentials = _make_credentials()
        bank_account = _make_bank_account()
        mock_adapter.fetch_accounts.return_value = [bank_account]
        mock_import_service.import_bank_account.return_value = (
            Mock(id=uuid4()),
            Mock(),
        )

        # Act
        result = await command_with_credential_repo.execute(
            credentials=provided_credentials,
            blz="50031000",  # Not used for loading since credentials provided
        )

        # Assert
        assert result.success is True
        mock_credential_repo.find_by_user_and_blz.assert_not_called()
        mock_adapter.connect.assert_called_once_with(provided_credentials)
        mock_credential_repo.update_last_used.assert_not_called()
