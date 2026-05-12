"""Unit tests for DiscoverAccountsCommand (credential loading and bank discovery)."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from swen.application.banking.commands import DiscoverAccountsCommand
from swen.domain.banking.value_objects import BankAccount, BankCredentials
from swen.domain.shared.value_objects.secure_string import SecureString

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_credentials(blz="50031000") -> BankCredentials:
    return BankCredentials(
        blz=blz,
        username=SecureString("user"),
        pin=SecureString("123456"),
    )


def _make_bank_account(iban="DE89370400440532013000") -> BankAccount:
    return BankAccount(
        iban=iban,
        account_number="532013000",
        blz="37040044",
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
        bank_name="Test Bank",
        balance=Decimal("1000.00"),
    )


@pytest.fixture
def mock_fetch_service():
    service = AsyncMock()
    service.fetch_accounts = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_credential_repo():
    repo = AsyncMock()
    repo.find_by_blz = AsyncMock(return_value=None)
    repo.get_tan_settings = AsyncMock(return_value=(None, None))
    return repo


@pytest.fixture
def command(mock_fetch_service, mock_credential_repo):
    return DiscoverAccountsCommand(
        bank_fetch_service=mock_fetch_service,
        credential_repo=mock_credential_repo,
    )


class TestDiscoverAccountsCommand:
    """Test credential loading and account discovery in DiscoverAccountsCommand."""

    @pytest.mark.asyncio
    async def test_returns_empty_result_when_no_credentials(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """Should return empty account list and skip fetch when no credentials found."""
        mock_credential_repo.find_by_blz.return_value = None

        result = await command.execute(blz="50031000")

        assert result.blz == "50031000"
        assert result.accounts == []
        mock_fetch_service.fetch_accounts.assert_not_called()

    @pytest.mark.asyncio
    async def test_loads_credentials_and_fetches_accounts(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """Should load credentials, call fetch_accounts with correct TAN settings."""
        blz = "50031000"
        stored_creds = _make_credentials(blz)
        mock_credential_repo.find_by_blz.return_value = stored_creds
        mock_credential_repo.get_tan_settings.return_value = ("946", None)
        mock_fetch_service.fetch_accounts.return_value = [_make_bank_account()]

        result = await command.execute(blz=blz)

        mock_credential_repo.find_by_blz.assert_called_once_with(blz)
        mock_fetch_service.fetch_accounts.assert_called_once_with(
            credentials=stored_creds, tan_method="946", tan_medium=None
        )
        assert result.blz == blz
        assert len(result.accounts) == 1

    @pytest.mark.asyncio
    async def test_discovered_account_has_default_name(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """Default name is generated from bank_name + account_type."""
        mock_credential_repo.find_by_blz.return_value = _make_credentials()
        mock_fetch_service.fetch_accounts.return_value = [_make_bank_account()]

        result = await command.execute(blz="50031000")

        assert result.accounts[0].default_name == "Test Bank - Girokonto"

    @pytest.mark.asyncio
    async def test_discovered_account_falls_back_to_account_holder_name(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """Default name falls back to account_holder when bank_name is absent."""
        account_without_bank_name = BankAccount(
            iban="DE89370400440532013000",
            account_number="532013000",
            blz="37040044",
            account_holder="Max Mustermann",
            account_type="Sparkonto",
            currency="EUR",
            bank_name=None,
        )
        mock_credential_repo.find_by_blz.return_value = _make_credentials()
        mock_fetch_service.fetch_accounts.return_value = [account_without_bank_name]

        result = await command.execute(blz="50031000")

        assert result.accounts[0].default_name == "Max Mustermann - Sparkonto"

    @pytest.mark.asyncio
    async def test_balance_serialized_as_string(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """Decimal balance from BankAccount is stored as string in DiscoveredAccountDTO."""
        mock_credential_repo.find_by_blz.return_value = _make_credentials()
        mock_fetch_service.fetch_accounts.return_value = [_make_bank_account()]

        result = await command.execute(blz="50031000")

        assert result.accounts[0].balance == "1000.00"

    @pytest.mark.asyncio
    async def test_result_is_frozen_dto(
        self,
        command,
        mock_credential_repo,
        mock_fetch_service,
    ):
        """BankDiscoveryResultDTO and its children are frozen (safe to round-trip)."""
        mock_credential_repo.find_by_blz.return_value = _make_credentials()
        mock_fetch_service.fetch_accounts.return_value = [_make_bank_account()]

        result = await command.execute(blz="50031000")

        # Verify immutability
        with pytest.raises(Exception):
            result.accounts[0].iban = "tampered"  # type: ignore[misc]
