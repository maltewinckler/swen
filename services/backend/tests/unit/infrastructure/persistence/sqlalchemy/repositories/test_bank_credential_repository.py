"""Unit tests for BankCredentialRepository (ACL orchestration layer)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from swen.domain.banking.repositories.bank_credential_repository import (
    BankCredentialRepository,
)
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.security.entities.stored_bank_credentials import (
    StoredBankCredentials,
)
from swen.domain.security.services.encryption_service import EncryptionService
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankCredentialRepositorySQLAlchemy,
)

# Fixed UUID for testing
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@dataclass(frozen=True)
class MockCurrentUser:
    """Mock CurrentUser for testing."""

    user_id: UUID
    email: str = "test@example.com"


@pytest.fixture
def mock_encryption_service():
    """Mock encryption service for unit testing."""
    service = Mock(spec=EncryptionService)
    service.encrypt = Mock(side_effect=lambda text: f"encrypted_{text}".encode())
    service.decrypt = Mock(
        side_effect=lambda data: data.decode().replace("encrypted_", ""),
    )
    return service


@pytest.fixture
def mock_stored_repo():
    """Mock StoredBankCredentialsRepository for unit testing."""
    return AsyncMock()


@pytest.fixture
def mock_current_user():
    """Mock CurrentUser for testing."""
    return MockCurrentUser(user_id=TEST_USER_ID)


@pytest.fixture
def repository(mock_stored_repo, mock_encryption_service, mock_current_user):
    """Create repository with mocked dependencies."""
    return BankCredentialRepositorySQLAlchemy(
        stored_credentials_repo=mock_stored_repo,
        encryption_service=mock_encryption_service,
        current_user=mock_current_user,
    )


class TestBankCredentialRepositorySave:
    """Test saving credentials through ACL."""

    @pytest.mark.asyncio
    async def test_save_encrypts_and_delegates(
        self,
        repository,
        mock_stored_repo,
        mock_encryption_service,
    ):
        """Should encrypt credentials and delegate to stored repository."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="12345678",
            username="testuser",
            pin="1234",
            endpoint="https://banking.test.de/fints",
        )

        # Act
        result = await repository.save(credentials, label="Test Bank")

        # Assert - encryption service was called
        assert mock_encryption_service.encrypt.call_count == 2
        mock_encryption_service.encrypt.assert_any_call("testuser")
        mock_encryption_service.encrypt.assert_any_call("1234")

        # Assert - stored repository was called with encrypted data
        mock_stored_repo.save.assert_called_once()
        call_args = mock_stored_repo.save.call_args
        stored_cred = call_args[0][0]

        assert isinstance(stored_cred, StoredBankCredentials)
        assert stored_cred.user_id == TEST_USER_ID
        assert stored_cred.blz == "12345678"
        assert stored_cred.endpoint == "https://banking.test.de/fints"
        assert stored_cred.username_encrypted == b"encrypted_testuser"
        assert stored_cred.pin_encrypted == b"encrypted_1234"
        assert stored_cred.label == "Test Bank"

        # Assert - returns credential ID
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_uses_optional_label(
        self,
        repository,
        mock_stored_repo,
    ):
        """Should use provided label."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="1234",
            endpoint="https://banking.triodos.de/fints",
        )

        # Act
        await repository.save(credentials, label=None)

        # Assert - label should be None
        call_args = mock_stored_repo.save.call_args
        stored_cred = call_args[0][0]
        assert stored_cred.label is None


class TestBankCredentialRepositoryFindByBlz:
    """Test finding credentials by BLZ."""

    @pytest.mark.asyncio
    async def test_find_decrypts_and_returns_credentials(
        self,
        repository,
        mock_stored_repo,
        mock_encryption_service,
    ):
        """Should retrieve encrypted credentials and decrypt them."""
        # Arrange
        blz = "12345678"

        stored = StoredBankCredentials(
            id="test-id-123",
            user_id=TEST_USER_ID,
            blz=blz,
            endpoint="https://banking.test.de/fints",
            username_encrypted=b"encrypted_testuser",
            pin_encrypted=b"encrypted_1234",
            encryption_version=1,
            label="Test Bank",
            is_active=True,
            tan_method=None,
            tan_medium=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_used_at=None,
        )
        mock_stored_repo.find_by_blz.return_value = stored

        # Act
        result = await repository.find_by_blz(blz)

        # Assert - stored repository was called
        mock_stored_repo.find_by_blz.assert_called_once_with(blz)

        # Assert - decryption service was called
        assert mock_encryption_service.decrypt.call_count == 2
        mock_encryption_service.decrypt.assert_any_call(b"encrypted_testuser")
        mock_encryption_service.decrypt.assert_any_call(b"encrypted_1234")

        # Assert - returns decrypted BankCredentials
        assert isinstance(result, BankCredentials)
        assert result.blz == blz
        assert result.endpoint == "https://banking.test.de/fints"
        assert result.username.get_value() == "testuser"
        assert result.pin.get_value() == "1234"

    @pytest.mark.asyncio
    async def test_find_returns_none_when_not_found(
        self,
        repository,
        mock_stored_repo,
    ):
        """Should return None when credentials don't exist."""
        # Arrange
        mock_stored_repo.find_by_blz.return_value = None

        # Act
        result = await repository.find_by_blz("12345678")

        # Assert
        assert result is None


class TestBankCredentialRepositoryFindAll:
    """Test finding all credentials for the current user."""

    @pytest.mark.asyncio
    async def test_find_all_returns_metadata(
        self,
        repository,
        mock_stored_repo,
    ):
        """Should retrieve metadata for all credentials."""
        # Arrange
        now = datetime.now(timezone.utc)
        stored_list = [
            StoredBankCredentials(
                id="cred-id-1",
                user_id=TEST_USER_ID,
                blz="12345678",
                endpoint="https://bank1.test.de/fints",
                username_encrypted=b"encrypted_user1",
                pin_encrypted=b"encrypted_pin1",
                encryption_version=1,
                label="Bank 1",
                is_active=True,
                tan_method=None,
                tan_medium=None,
                created_at=now,
                updated_at=now,
                last_used_at=None,
            ),
            StoredBankCredentials(
                id="cred-id-2",
                user_id=TEST_USER_ID,
                blz="87654321",
                endpoint="https://bank2.test.de/fints",
                username_encrypted=b"encrypted_user2",
                pin_encrypted=b"encrypted_pin2",
                encryption_version=1,
                label="Bank 2",
                is_active=True,
                tan_method=None,
                tan_medium=None,
                created_at=now,
                updated_at=now,
                last_used_at=None,
            ),
        ]
        mock_stored_repo.find_all.return_value = stored_list

        # Act
        result = await repository.find_all()

        # Assert
        assert len(result) == 2
        assert result[0] == ("cred-id-1", "12345678", "Bank 1")
        assert result[1] == ("cred-id-2", "87654321", "Bank 2")


class TestBankCredentialRepositoryDelete:
    """Test deleting credentials."""

    @pytest.mark.asyncio
    async def test_delete_delegates_to_stored_repo(self, repository, mock_stored_repo):
        """Should delegate delete to stored repository."""
        # Arrange
        blz = "12345678"
        mock_stored_repo.delete.return_value = True

        # Act
        result = await repository.delete(blz)

        # Assert
        mock_stored_repo.delete.assert_called_once_with(blz)
        assert result is True


class TestBankCredentialRepositoryUpdateLastUsed:
    """Test updating last used timestamp."""

    @pytest.mark.asyncio
    async def test_update_last_used_delegates_to_stored_repo(
        self,
        repository,
        mock_stored_repo,
    ):
        """Should delegate update to stored repository."""
        # Arrange
        blz = "12345678"

        # Act
        await repository.update_last_used(blz)

        # Assert
        mock_stored_repo.update_last_used.assert_called_once_with(blz)


class TestBankCredentialRepositoryInterface:
    """Test that implementation conforms to interface."""

    def test_implements_bank_credential_repository(self):
        """Should implement BankCredentialRepository interface."""
        assert issubclass(
            BankCredentialRepositorySQLAlchemy,
            BankCredentialRepository,
        )

    def test_has_all_required_methods(self):
        """Should have all methods defined in interface."""
        required_methods = [
            "save",
            "find_by_blz",
            "find_all",
            "delete",
            "update_last_used",
            "get_tan_settings",
        ]

        for method in required_methods:
            assert hasattr(BankCredentialRepositorySQLAlchemy, method)
