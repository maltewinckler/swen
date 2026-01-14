"""Tests for BankAccountImportService."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from swen.application.services import BankAccountImportService
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount
from swen.domain.integration.entities import AccountMapping
from swen.domain.shared.exceptions import ValidationError
from swen.application.ports.identity import CurrentUser

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestBankAccountImportService:
    """Test cases for BankAccountImportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_account_repo = Mock()
        self.mock_mapping_repo = Mock()
        # AccountRepository methods are async in production
        self.mock_account_repo.find_by_account_number = AsyncMock(return_value=None)
        self.mock_account_repo.find_by_iban = AsyncMock(return_value=None)
        self.current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")
        self.service = BankAccountImportService(
            account_repository=self.mock_account_repo,
            mapping_repository=self.mock_mapping_repo,
            current_user=self.current_user,
        )

    @pytest.mark.asyncio
    async def test_import_new_bank_account(self):
        """Test importing a new bank account creates account and mapping."""
        # Arrange
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        # No existing mapping
        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act - user_id is now obtained from CurrentUser in constructor
        asset_account, mapping = await self.service.import_bank_account(bank_account)

        # Assert
        assert asset_account.name == "DKB - Girokonto"
        assert asset_account.account_type == AccountType.ASSET
        # Uses generated human-facing account_number derived from IBAN
        assert asset_account.account_number == "BA-32013000"
        assert asset_account.iban == "DE89370400440532013000"
        assert asset_account.default_currency.code == "EUR"

        assert mapping.iban == "DE89370400440532013000"
        assert mapping.accounting_account_id == asset_account.id
        assert mapping.account_name == "DKB - Girokonto"
        assert mapping.is_active is True

        # Verify save was called
        self.mock_account_repo.save.assert_called_once()
        self.mock_mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_reuses_existing_account_by_iban_when_mapping_missing(self):
        """Reuse existing account by IBAN when mapping is missing."""
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        existing_account = Account(
            name="Existing Bank Account",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
            default_currency=Currency("EUR"),
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.find_by_iban = AsyncMock(return_value=existing_account)
        self.mock_mapping_repo.save = AsyncMock()
        self.mock_account_repo.save = AsyncMock()

        account, mapping = await self.service.import_bank_account(bank_account)

        assert account is existing_account
        assert mapping.iban == "DE89370400440532013000"
        assert mapping.accounting_account_id == existing_account.id
        self.mock_account_repo.save.assert_not_called()
        self.mock_mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_bank_account_account_number_collision_adds_suffix(self):
        """Account number collision should add suffix to avoid duplicates."""
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Simulate collision for base "BA-32013000", free for "BA-32013000-2"
        existing = Account(
            name="Existing",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            iban="DE00000000000000000000",
            default_currency=Currency("EUR"),
        )
        self.mock_account_repo.find_by_account_number = AsyncMock(
            side_effect=[existing, None],
        )

        asset_account, _mapping = await self.service.import_bank_account(bank_account)
        assert asset_account.account_number == "BA-32013000-2"

    @pytest.mark.asyncio
    async def test_import_existing_bank_account_is_idempotent(self):
        """Test importing same bank account returns existing mapping."""
        # Arrange
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        # Existing mapping
        existing_account_id = uuid4()
        existing_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=existing_account_id,
            account_name="DKB - Girokonto",
            user_id=TEST_USER_ID,
        )

        existing_account = Account(
            name="DKB - Girokonto",
            account_type=AccountType.ASSET,
            account_number="0532013000",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
            default_currency=Currency("EUR"),
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=existing_mapping)
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)

        # Act
        asset_account, mapping = await self.service.import_bank_account(bank_account)

        # Assert - Returns existing, doesn't create new
        assert mapping.id == existing_mapping.id
        assert asset_account.name == "DKB - Girokonto"

        # Should NOT call save for existing mapping
        self.mock_account_repo.save = AsyncMock()
        assert not self.mock_account_repo.save.called

    @pytest.mark.asyncio
    async def test_import_bank_account_without_bank_name(self):
        """Test importing bank account without bank name uses account holder."""
        # Arrange
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name=None,  # No bank name
            currency="EUR",
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        asset_account, _mapping = await self.service.import_bank_account(bank_account)

        # Assert - Uses account holder as fallback
        assert "Max Mustermann" in asset_account.name
        assert asset_account.account_type == AccountType.ASSET

    @pytest.mark.asyncio
    async def test_import_multiple_bank_accounts(self):
        """Test importing multiple bank accounts at once."""
        # Arrange
        accounts = [
            BankAccount(
                iban="DE89370400440532013001",
                account_number="0532013001",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Girokonto",
                bank_name="DKB",
                currency="EUR",
            ),
            BankAccount(
                iban="DE89370400440532013002",
                account_number="0532013002",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Tagesgeld",
                bank_name="DKB",
                currency="EUR",
            ),
        ]

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        results = await self.service.import_multiple_bank_accounts(accounts)

        # Assert
        assert len(results) == 2
        assert results[0][0].name == "DKB - Girokonto"
        assert results[1][0].name == "DKB - Tagesgeld"

        # Verify both were saved
        assert self.mock_account_repo.save.call_count == 2
        assert self.mock_mapping_repo.save.call_count == 2

    @pytest.mark.asyncio
    async def test_get_or_create_asset_account_raises_when_no_mapping(self):
        """Test get_or_create raises ValueError when no mapping exists."""
        # Arrange
        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="No account mapping found"):
            await self.service.get_or_create_asset_account(
                iban="DE89370400440532013000",
            )

    @pytest.mark.asyncio
    async def test_get_or_create_asset_account_returns_existing(self):
        """Test get_or_create returns existing account."""
        # Arrange
        existing_account_id = uuid4()
        existing_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=existing_account_id,
            account_name="Test Account",
            user_id=TEST_USER_ID,
        )

        # Create existing account (without id parameter - it's auto-generated)
        existing_account = Account(
            name="Test Account",
            account_type=AccountType.ASSET,
            account_number="0532013000",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
            default_currency=Currency("EUR"),
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=existing_mapping)
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)

        # Act
        result = await self.service.get_or_create_asset_account(
            iban="DE89370400440532013000",
        )

        # Assert
        assert result.name == "Test Account"
        assert result.account_type == AccountType.ASSET


class TestBankAccountImportServiceCustomName:
    """Test cases for custom name functionality in BankAccountImportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_account_repo = Mock()
        self.mock_mapping_repo = Mock()
        # AccountRepository methods are async in production
        self.mock_account_repo.find_by_account_number = AsyncMock(return_value=None)
        self.mock_account_repo.find_by_iban = AsyncMock(return_value=None)
        self.current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")
        self.service = BankAccountImportService(
            account_repository=self.mock_account_repo,
            mapping_repository=self.mock_mapping_repo,
            current_user=self.current_user,
        )

    @pytest.mark.asyncio
    async def test_import_with_custom_name(self):
        """Test importing a bank account with a custom name."""
        # Arrange
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        asset_account, mapping = await self.service.import_bank_account(
            bank_account,
            custom_name="My Primary Account",
        )

        # Assert - custom name used instead of generated
        assert asset_account.name == "My Primary Account"
        assert mapping.account_name == "My Primary Account"

    @pytest.mark.asyncio
    async def test_import_without_custom_name_uses_default(self):
        """Test importing without custom name falls back to generated name."""
        # Arrange
        bank_account = BankAccount(
            iban="DE89370400440532013000",
            account_number="0532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Girokonto",
            bank_name="DKB",
            currency="EUR",
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        asset_account, mapping = await self.service.import_bank_account(
            bank_account,
            custom_name=None,
        )

        # Assert - default generated name
        assert asset_account.name == "DKB - Girokonto"
        assert mapping.account_name == "DKB - Girokonto"

    @pytest.mark.asyncio
    async def test_import_multiple_with_custom_names(self):
        """Test importing multiple accounts with custom names mapping."""
        # Arrange
        accounts = [
            BankAccount(
                iban="DE89370400440532013001",
                account_number="0532013001",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Girokonto",
                bank_name="DKB",
                currency="EUR",
            ),
            BankAccount(
                iban="DE89370400440532013002",
                account_number="0532013002",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Tagesgeld",
                bank_name="DKB",
                currency="EUR",
            ),
        ]

        custom_names = {
            "DE89370400440532013001": "Primary Checking",
            # Note: second account has no custom name
        }

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        results = await self.service.import_multiple_bank_accounts(
            accounts,
            custom_names=custom_names,
        )

        # Assert
        assert len(results) == 2
        assert results[0][0].name == "Primary Checking"  # Custom name
        assert results[1][0].name == "DKB - Tagesgeld"  # Default generated


class TestBankAccountRenameService:
    """Test cases for rename functionality in BankAccountImportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_account_repo = Mock()
        self.mock_mapping_repo = Mock()
        self.current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")
        self.service = BankAccountImportService(
            account_repository=self.mock_account_repo,
            mapping_repository=self.mock_mapping_repo,
            current_user=self.current_user,
        )

    @pytest.mark.asyncio
    async def test_rename_bank_account_success(self):
        """Test renaming a bank account updates both Account and AccountMapping."""
        # Arrange
        existing_account = Account(
            name="DKB - Girokonto",
            account_type=AccountType.ASSET,
            account_number="DE89370400440532013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        existing_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=existing_account.id,
            account_name="DKB - Girokonto",
            user_id=TEST_USER_ID,
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=existing_mapping)
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        result = await self.service.rename_bank_account(
            iban="DE89370400440532013000",
            new_name="My Primary Account",
        )

        # Assert - returns BankAccountDTO
        assert result.name == "My Primary Account"
        assert result.iban == "DE89370400440532013000"

        # Verify both domain entities were saved
        self.mock_account_repo.save.assert_called_once()
        self.mock_mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_rename_bank_account_no_mapping_raises_error(self):
        """Test renaming fails when no mapping exists for IBAN."""
        # Arrange
        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="No account mapping found"):
            await self.service.rename_bank_account(
                iban="DE89370400440532013000",
                new_name="New Name",
            )

    @pytest.mark.asyncio
    async def test_rename_bank_account_no_account_raises_error(self):
        """Test renaming fails when account not found."""
        # Arrange
        existing_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=uuid4(),
            account_name="Old Name",
            user_id=TEST_USER_ID,
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=existing_mapping)
        self.mock_account_repo.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Mapping exists but account not found"):
            await self.service.rename_bank_account(
                iban="DE89370400440532013000",
                new_name="New Name",
            )

    @pytest.mark.asyncio
    async def test_rename_bank_account_empty_name_raises_error(self):
        """Test renaming with empty name raises ValueError."""
        # Arrange
        existing_account = Account(
            name="Old Name",
            account_type=AccountType.ASSET,
            account_number="DE89370400440532013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        existing_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=existing_account.id,
            account_name="Old Name",
            user_id=TEST_USER_ID,
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=existing_mapping)
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)

        # Act & Assert
        with pytest.raises(ValidationError):
            await self.service.rename_bank_account(
                iban="DE89370400440532013000",
                new_name="",
            )
