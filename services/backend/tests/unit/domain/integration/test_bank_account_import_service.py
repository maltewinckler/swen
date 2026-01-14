"""Tests for BankAccountImportService."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from swen.application.services import BankAccountImportService
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount
from swen.domain.integration.entities import AccountMapping
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

        # Act
        asset_account, mapping = await self.service.import_bank_account(
            bank_account,
        )

        # Assert
        assert asset_account.name == "DKB - Girokonto"
        assert asset_account.account_type == AccountType.ASSET
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
        """If mapping is missing but an account exists for the IBAN, reuse it and create mapping."""
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

        asset_account, mapping = await self.service.import_bank_account(bank_account)

        assert asset_account is existing_account
        assert mapping.accounting_account_id == existing_account.id
        self.mock_account_repo.save.assert_not_called()
        self.mock_mapping_repo.save.assert_called_once()

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
            account_number="DE89370400440532013000",  # IBAN as account number
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(
            return_value=existing_mapping,
        )
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        asset_account, mapping = await self.service.import_bank_account(
            bank_account,
        )

        # Assert - returns existing
        assert asset_account == existing_account
        assert mapping == existing_mapping

        # Should NOT create new account or mapping
        self.mock_account_repo.save.assert_not_called()
        self.mock_mapping_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_without_bank_name_uses_account_holder(self):
        """Test account name fallback when bank name not available."""
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
        asset_account, mapping = await self.service.import_bank_account(
            bank_account,
        )

        # Assert - uses account holder as fallback
        assert asset_account.name == "Max Mustermann - Girokonto"
        assert mapping.account_name == "Max Mustermann - Girokonto"

    @pytest.mark.asyncio
    async def test_import_multiple_bank_accounts(self):
        """Test importing multiple bank accounts at once."""
        # Arrange
        bank_accounts = [
            BankAccount(
                iban="DE89370400440532013000",
                account_number="0532013000",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Girokonto",
                bank_name="DKB",
                currency="EUR",
            ),
            BankAccount(
                iban="DE89370400440532013001",
                account_number="0532013001",
                blz="37040044",
                account_holder="Max Mustermann",
                account_type="Sparkonto",
                bank_name="DKB",
                currency="EUR",
            ),
        ]

        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)
        self.mock_account_repo.save = AsyncMock()
        self.mock_mapping_repo.save = AsyncMock()

        # Act
        results = await self.service.import_multiple_bank_accounts(
            bank_accounts,
        )

        # Assert
        assert len(results) == 2
        assert results[0][0].name == "DKB - Girokonto"
        assert results[1][0].name == "DKB - Sparkonto"

        # Verify save was called twice for each
        assert self.mock_account_repo.save.call_count == 2
        assert self.mock_mapping_repo.save.call_count == 2

    @pytest.mark.asyncio
    async def test_get_or_create_asset_account_existing(self):
        """Test getting existing asset account by IBAN."""
        # Arrange
        iban = "DE89370400440532013000"
        existing_account_id = uuid4()
        existing_mapping = AccountMapping(
            iban=iban,
            accounting_account_id=existing_account_id,
            account_name="DKB - Girokonto",
            user_id=TEST_USER_ID,
        )
        existing_account = Account(
            name="DKB - Girokonto",
            account_type=AccountType.ASSET,
            account_number=iban,  # IBAN as account number
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        self.mock_mapping_repo.find_by_iban = AsyncMock(
            return_value=existing_mapping,
        )
        self.mock_account_repo.find_by_id = AsyncMock(return_value=existing_account)

        # Act
        account = await self.service.get_or_create_asset_account(iban)

        # Assert
        assert account == existing_account

    @pytest.mark.asyncio
    async def test_get_or_create_asset_account_not_found(self):
        """Test error when no mapping exists."""
        # Arrange
        iban = "DE89370400440532013000"
        self.mock_mapping_repo.find_by_iban = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="No account mapping found"):
            await self.service.get_or_create_asset_account(iban)
