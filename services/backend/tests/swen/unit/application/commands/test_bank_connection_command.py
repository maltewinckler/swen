"""Unit tests for BankConnectionCommand."""

from unittest.mock import AsyncMock
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
        mock_fetch_service = AsyncMock()
        mock_import_service = AsyncMock()

        bank_creds = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
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

        mock_fetch_service.fetch_accounts.return_value = [bank_acct]
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            mapping,
        )

        mock_credential_repo = AsyncMock()
        mock_credential_repo.find_by_blz.return_value = (
            None  # No credential needed when passing credentials
        )

        command = BankConnectionCommand(
            bank_fetch_service=mock_fetch_service,
            import_service=mock_import_service,
            credential_repo=mock_credential_repo,
        )

        # Act - pass BLZ instead of credentials
        result = await command.execute(blz="50031000", bank_accounts=[bank_acct])

        # Assert
        assert result.success is True
        assert result.bank_code == "50031000"
        assert result.accounts_count == 1
        assert result.accounts_imported[0].iban == "DE89370400440532013000"

        # Verify fetch was NOT called since we provided accounts directly
        mock_fetch_service.fetch_accounts.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_with_no_accounts(self):
        """Test connection when bank returns no accounts."""
        # Arrange
        mock_fetch_service = AsyncMock()
        mock_fetch_service.fetch_accounts.return_value = []

        mock_credential_repo = AsyncMock()
        mock_credential_repo.find_by_blz.return_value = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
        )

        command = BankConnectionCommand(
            bank_fetch_service=mock_fetch_service,
            import_service=AsyncMock(),
            credential_repo=mock_credential_repo,
        )

        # Act - fetch from bank but get no accounts
        result = await command.execute(blz="50031000")

        # Assert
        assert result.success is True
        assert result.accounts_count == 0
        assert result.error_message is None
        assert result.warning_message == "No accounts found at bank"
        mock_fetch_service.fetch_accounts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failure."""
        # Arrange
        mock_fetch_service = AsyncMock()
        mock_fetch_service.fetch_accounts.side_effect = Exception("Invalid credentials")

        mock_credential_repo = AsyncMock()
        mock_credential_repo.find_by_blz.return_value = BankCredentials(
            blz="50031000",
            username=SecureString("testuser"),
            pin=SecureString("1234"),
        )

        command = BankConnectionCommand(
            bank_fetch_service=mock_fetch_service,
            import_service=AsyncMock(),
            credential_repo=mock_credential_repo,
        )

        # Act - fetch from bank triggers error
        result = await command.execute(blz="50031000")

        # Assert
        assert result.success is False
        assert "Invalid credentials" in str(result.error_message)

    @pytest.mark.asyncio
    async def test_result_to_dict_serialization(self):
        """Test that ConnectionResult can be serialized to dict."""
        # Arrange
        mock_fetch_service = AsyncMock()
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

        mock_fetch_service.fetch_accounts.return_value = [bank_acct]
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            mapping,
        )

        command = BankConnectionCommand(
            bank_fetch_service=mock_fetch_service,
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )

        # Act - pass bank_accounts directly to skip credential lookup
        result = await command.execute(blz="50031000", bank_accounts=[bank_acct])
        result_dict = result.to_dict()

        # Assert
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["bank_code"] == "50031000"
