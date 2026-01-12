"""Unit tests for TransactionSyncCommand with credential loading."""

from dataclasses import dataclass
from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from swen.application.commands import TransactionSyncCommand
from swen.domain.banking.value_objects import BankCredentials
from swen.domain.integration.entities import AccountMapping
from swen.domain.shared.value_objects.secure_string import SecureString

IBAN = "DE89370400440532013000"
BLZ = "37040044"  # Extracted from IBAN
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@dataclass(frozen=True)
class MockUserContext:
    """Mock UserContext for testing."""

    user_id: UUID
    email: str = "test@example.com"


def _make_credentials() -> BankCredentials:
    return BankCredentials(
        blz=BLZ,
        username=SecureString("user"),
        pin=SecureString("123456"),
        endpoint="https://fints.example.com/fints",
    )


def _make_mapping(active: bool = True) -> AccountMapping:
    return AccountMapping(
        iban=IBAN,
        accounting_account_id=uuid4(),
        account_name="Test Account",
        user_id=TEST_USER_ID,
        is_active=active,
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
    adapter.fetch_transactions = AsyncMock(return_value=[])
    adapter.disconnect = AsyncMock()
    return adapter


@pytest.fixture
def mock_import_service():
    """Mock import service."""
    service = AsyncMock()
    service.import_transactions = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_mapping_repo():
    """Mock mapping repository."""
    repo = AsyncMock()
    repo.find_by_iban = AsyncMock(return_value=_make_mapping())
    return repo


@pytest.fixture
def mock_import_repo():
    """Mock import repository."""
    repo = AsyncMock()
    repo.find_by_iban = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_credential_repo():
    """Mock credential repository (user-scoped, no user_id params)."""
    repo = AsyncMock()
    repo.find_by_blz = AsyncMock()
    repo.update_last_used = AsyncMock()
    repo.get_tan_settings = AsyncMock(return_value=(None, None))
    return repo


@pytest.fixture
def mock_bank_transaction_repo():
    """Mock bank transaction repository."""
    repo = AsyncMock()
    repo.save_batch_with_deduplication = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_user_context():
    """Mock user context."""
    return MockUserContext(user_id=TEST_USER_ID)


@pytest.fixture
def command_with_credential_repo(
    mock_adapter,
    mock_import_service,
    mock_mapping_repo,
    mock_import_repo,
    mock_credential_repo,
    mock_bank_transaction_repo,
    mock_user_context,
):
    """Create command with credential repository."""
    return TransactionSyncCommand(
        bank_adapter=mock_adapter,
        import_service=mock_import_service,
        mapping_repo=mock_mapping_repo,
        import_repo=mock_import_repo,
        user_context=mock_user_context,
        credential_repo=mock_credential_repo,
        bank_transaction_repo=mock_bank_transaction_repo,
    )


class TestTransactionSyncCommandWithCredentialLoading:
    """Test credential loading functionality.

    Note: The credential repository is now user-scoped, so user_id is not
    passed to repository methods or execute() - it's implicit in the
    UserContext passed to the constructor.
    """

    @pytest.mark.asyncio
    async def test_loads_credentials_from_storage_when_no_credentials_provided(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
    ):
        """Should load credentials from repository when none provided."""
        # Arrange
        stored_credentials = _make_credentials()
        mock_credential_repo.find_by_blz.return_value = stored_credentials

        # Act
        result = await command_with_credential_repo.execute(
            iban=IBAN,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Assert
        assert result.success is True
        mock_credential_repo.find_by_blz.assert_called_once_with(BLZ)
        mock_adapter.connect.assert_called_once_with(stored_credentials)

    @pytest.mark.asyncio
    async def test_updates_last_used_after_successful_sync_with_stored_credentials(
        self,
        command_with_credential_repo,
        mock_credential_repo,
    ):
        """Should update last_used timestamp when using stored credentials."""
        # Arrange
        stored_credentials = _make_credentials()
        mock_credential_repo.find_by_blz.return_value = stored_credentials

        # Act
        result = await command_with_credential_repo.execute(
            iban=IBAN,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Assert
        assert result.success is True
        mock_credential_repo.update_last_used.assert_called_once_with(BLZ)

    @pytest.mark.asyncio
    async def test_does_not_update_last_used_when_credentials_provided_directly(
        self,
        command_with_credential_repo,
        mock_credential_repo,
    ):
        """Should not update last_used when credentials provided directly."""
        # Arrange
        credentials = _make_credentials()

        # Act
        result = await command_with_credential_repo.execute(
            iban=IBAN,
            credentials=credentials,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Assert
        assert result.success is True
        mock_credential_repo.find_by_blz.assert_not_called()
        mock_credential_repo.update_last_used.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_stored_credentials_not_found(
        self,
        command_with_credential_repo,
        mock_credential_repo,
    ):
        """Should return error result when stored credentials don't exist."""
        # Arrange
        mock_credential_repo.find_by_blz.return_value = None

        # Act
        result = await command_with_credential_repo.execute(
            iban="DE89370400440532013000",
        )

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "No stored credentials found" in result.error_message

    @pytest.mark.asyncio
    async def test_raises_error_when_credential_repo_not_provided(
        self,
        mock_adapter,
        mock_import_service,
        mock_mapping_repo,
        mock_import_repo,
        mock_bank_transaction_repo,
        mock_user_context,
    ):
        """Should return error result when trying to load credentials without repo."""
        # Arrange - command without credential_repo
        command = TransactionSyncCommand(
            bank_adapter=mock_adapter,
            import_service=mock_import_service,
            mapping_repo=mock_mapping_repo,
            import_repo=mock_import_repo,
            user_context=mock_user_context,
            credential_repo=None,  # No credential repository
            bank_transaction_repo=mock_bank_transaction_repo,
        )

        # Act
        result = await command.execute(
            iban="DE89370400440532013000",
        )

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "credential_repo not provided" in result.error_message

    @pytest.mark.asyncio
    async def test_extracts_blz_from_german_iban(
        self,
        command_with_credential_repo,
        mock_credential_repo,
    ):
        """Should correctly extract BLZ from German IBAN."""
        # Arrange
        iban = "DE89370400440532013000"  # BLZ = 37040044
        stored_credentials = _make_credentials()
        mock_credential_repo.find_by_blz.return_value = stored_credentials

        # Act
        await command_with_credential_repo.execute(
            iban=iban,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Assert
        mock_credential_repo.find_by_blz.assert_called_once_with("37040044")

    @pytest.mark.asyncio
    async def test_raises_error_for_non_german_iban(
        self,
        command_with_credential_repo,
    ):
        """Should return error result for non-German IBAN."""
        # Arrange
        non_german_iban = "FR1420041010050500013M02606"

        # Act
        result = await command_with_credential_repo.execute(
            iban=non_german_iban,
        )

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "Cannot extract BLZ from IBAN" in result.error_message

    @pytest.mark.asyncio
    async def test_prefers_provided_credentials_over_loading(
        self,
        command_with_credential_repo,
        mock_credential_repo,
        mock_adapter,
    ):
        """Should use provided credentials over loading from storage."""
        # Arrange
        provided_credentials = _make_credentials()

        # Act
        result = await command_with_credential_repo.execute(
            iban=IBAN,
            credentials=provided_credentials,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # Assert
        assert result.success is True
        mock_credential_repo.find_by_blz.assert_not_called()
        mock_adapter.connect.assert_called_once_with(provided_credentials)
