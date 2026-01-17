"""Unit tests for BankConnectionCommand."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from swen.application.commands import BankConnectionCommand
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount, BankCredentials
from swen.domain.integration.entities import AccountMapping
from swen.domain.shared.value_objects.secure_string import SecureString

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestBankConnectionCommand:
    """Test suite for BankConnectionCommand."""

    @pytest.mark.asyncio
    async def test_successful_connection_and_import(self):
        """Test successful bank connection and account import."""
        # Arrange
        mock_adapter = AsyncMock()
        mock_import_service = AsyncMock()

        bank_creds = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
            endpoint="https://fints.example.com/fints",
        )

        bank_acct = BankAccount(
            iban="DE89370400440532013000",
            account_holder="Max Mustermann",
            account_number="532013000",
            blz="37040044",
            account_type="Girokonto",
            currency="EUR",
            bank_name="Test Bank",
        )

        accounting_acct = Account(
            name="Test Bank - Girokonto",
            account_type=AccountType.ASSET,
            account_number="1000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=accounting_acct.id,
            account_name="Test Bank - Girokonto",
            user_id=TEST_USER_ID,
        )

        mock_adapter.fetch_accounts.return_value = [bank_acct]
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            mapping,
        )

        command = BankConnectionCommand(
            bank_adapter=mock_adapter,
            import_service=mock_import_service,
        )

        # Act - user_id is now obtained from user-scoped repositories
        result = await command.execute(credentials=bank_creds)

        # Assert
        assert result.success is True
        assert result.bank_code == "50031000"
        assert result.accounts_count == 1
        assert result.accounts_imported[0].iban == "DE89370400440532013000"

        # Verify workflow
        mock_adapter.connect.assert_called_once_with(bank_creds)
        mock_adapter.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_with_no_accounts(self):
        """Test connection when bank returns no accounts."""
        # Arrange
        mock_adapter = AsyncMock()
        mock_adapter.fetch_accounts.return_value = []

        command = BankConnectionCommand(
            bank_adapter=mock_adapter,
            import_service=AsyncMock(),
        )

        bank_creds = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
            endpoint="https://fints.example.com/fints",
        )

        # Act - user_id is now obtained from user-scoped repositories
        result = await command.execute(credentials=bank_creds)

        # Assert
        assert result.success is True
        assert result.accounts_count == 0
        assert result.error_message is None
        assert result.warning_message == "No accounts found at bank"
        mock_adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failure."""
        # Arrange
        mock_adapter = AsyncMock()
        mock_adapter.connect.side_effect = Exception("Invalid credentials")
        # is_connected() is a sync method, not async
        mock_adapter.is_connected = Mock(return_value=False)

        command = BankConnectionCommand(
            bank_adapter=mock_adapter,
            import_service=AsyncMock(),
        )

        bank_creds = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
            endpoint="https://fints.example.com/fints",
        )

        # Act - user_id is now obtained from user-scoped repositories
        result = await command.execute(credentials=bank_creds)

        # Assert
        assert result.success is False
        assert "Invalid credentials" in str(result.error_message)

    @pytest.mark.asyncio
    async def test_result_to_dict_serialization(self):
        """Test that ConnectionResult can be serialized to dict."""
        # Arrange
        mock_adapter = AsyncMock()
        mock_import_service = AsyncMock()

        bank_acct = BankAccount(
            iban="DE89370400440532013000",
            account_holder="Max Mustermann",
            account_number="532013000",
            blz="37040044",
            account_type="Girokonto",
            currency="EUR",
            bank_name="Test Bank",
        )

        accounting_acct = Account(
            name="Test Bank - Girokonto",
            account_type=AccountType.ASSET,
            account_number="1000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=accounting_acct.id,
            account_name="Test Bank - Girokonto",
            user_id=TEST_USER_ID,
        )

        mock_adapter.fetch_accounts.return_value = [bank_acct]
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            mapping,
        )

        command = BankConnectionCommand(
            bank_adapter=mock_adapter,
            import_service=mock_import_service,
        )

        bank_creds = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
            endpoint="https://fints.example.com/fints",
        )

        # Act - user_id is now obtained from user-scoped repositories
        result = await command.execute(credentials=bank_creds)
        result_dict = result.to_dict()

        # Assert
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["bank_code"] == "50031000"
