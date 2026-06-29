"""Unit tests for CreateExternalAccountCommand."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from swen.application.integration.commands import CreateExternalAccountCommand
from swen.application.integration.dtos import ExternalAccountCreatedDTO
from swen.domain.accounting.entities import AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.services import ExternalAccountManagementService
from swen.domain.integration.services.external_account_management_service import (
    ExternalAccountResult,
)
from swen.domain.shared.current_user import CurrentUser

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_IBAN = "DE51120700700756557355"


def _make_command() -> tuple[
    CreateExternalAccountCommand,
    AsyncMock,
    AsyncMock,
    AsyncMock,
]:
    """Create command with mocked domain service."""
    management_service = AsyncMock(spec=ExternalAccountManagementService)
    account_repo = AsyncMock()
    mapping_repo = AsyncMock()
    transaction_repo = AsyncMock()

    command = CreateExternalAccountCommand(
        external_account_management_service=management_service,
    )

    return command, management_service, account_repo, mapping_repo


class TestCreateExternalAccountCommand:
    """Test cases for CreateExternalAccountCommand."""

    @pytest.mark.asyncio
    async def test_delegates_to_management_service(self):
        """Test that command delegates business logic to management service."""
        command, mgmt_service, _, _ = _make_command()

        # Create a mock result
        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "Test Account"
        mock_account.account_number = "EXT-56557355"

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "Test"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = MagicMock()
        mock_mapping.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"

        mock_result = ExternalAccountResult(
            account=mock_account,
            mapping=mock_mapping,
            transactions_reconciled=0,
            already_existed=True,
        )
        mgmt_service.create_or_find_external_account.return_value = mock_result

        # Act
        result = await command.execute(
            iban=TEST_IBAN,
            name="Test Account",
            currency="EUR",
            account_type=AccountType.ASSET,
            reconcile=True,
        )

        # Assert
        assert isinstance(result, ExternalAccountCreatedDTO)
        assert result.already_existed is True
        assert result.transactions_reconciled == 0
        mgmt_service.create_or_find_external_account.assert_called_once_with(
            iban=TEST_IBAN,
            name="Test Account",
            currency=Currency("EUR"),
            account_type=AccountType.ASSET,
            reconcile=True,
        )

    async def test_builds_dto_with_correct_fields(self):
        """Test that DTO is built with all correct fields."""
        command, mgmt_service, _, _ = _make_command()

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "Account Name"
        mock_account.account_number = "EXT-12345678"

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "Mapping Name"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = MagicMock()
        mock_mapping.created_at.isoformat.return_value = "2024-06-01T12:00:00+00:00"

        mgmt_service.create_or_find_external_account.return_value = (
            ExternalAccountResult(
                account=mock_account,
                mapping=mock_mapping,
                transactions_reconciled=5,
                already_existed=False,
            )
        )

        result = await command.execute(
            iban=TEST_IBAN,
            name="Test",
            currency="EUR",
            account_type=AccountType.ASSET,
            reconcile=True,
        )

        assert result.mapping.iban == TEST_IBAN
        assert result.mapping.account_name == "Mapping Name"
        assert result.mapping.accounting_account_name == "Account Name"
        assert result.mapping.accounting_account_number == "EXT-12345678"
        assert result.transactions_reconciled == 5
        assert result.already_existed is False

    @pytest.mark.asyncio
    async def test_passes_reconcile_flag_through(self):
        """Test that reconcile flag is passed through to service."""
        command, mgmt_service, _, _ = _make_command()

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "Test"
        mock_account.account_number = "EXT-12345678"
        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "Test"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = MagicMock()
        mock_mapping.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"

        mgmt_service.create_or_find_external_account.return_value = (
            ExternalAccountResult(
                account=mock_account,
                mapping=mock_mapping,
                transactions_reconciled=0,
                already_existed=True,
            )
        )

        # Act - reconcile=False
        await command.execute(
            iban=TEST_IBAN,
            name="Test",
            currency="EUR",
            account_type=AccountType.ASSET,
            reconcile=False,
        )

        # Assert
        call_args = mgmt_service.create_or_find_external_account.call_args
        assert call_args.kwargs["reconcile"] is False


class TestCreateExternalAccountCommandLiability:
    """Test cases for LIABILITY account type handling."""

    @pytest.mark.asyncio
    async def test_passes_liability_account_type_to_service(self):
        """Test that LIABILITY account type is passed through correctly."""
        command, mgmt_service, _, _ = _make_command()

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "Credit Card"
        mock_account.account_number = "LIA-56557355"
        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "Credit Card"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = MagicMock()
        mock_mapping.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"

        mgmt_service.create_or_find_external_account.return_value = (
            ExternalAccountResult(
                account=mock_account,
                mapping=mock_mapping,
                transactions_reconciled=0,
                already_existed=False,
            )
        )

        # Act
        await command.execute(
            iban=TEST_IBAN,
            name="Credit Card",
            currency="EUR",
            account_type=AccountType.LIABILITY,
            reconcile=True,
        )

        # Assert
        call_args = mgmt_service.create_or_find_external_account.call_args
        assert call_args.kwargs["account_type"] == AccountType.LIABILITY


class TestCreateExternalAccountCommandFromFactory:
    """Test the from_factory class method."""

    def test_from_factory_creates_command_with_service(self):
        """Test that from_factory creates command with management service."""
        # Create mock factory
        mock_factory = MagicMock()
        mock_factory.account_repository.return_value = AsyncMock()
        mock_factory.account_mapping_repository.return_value = AsyncMock()
        mock_factory.transaction_repository.return_value = AsyncMock()
        mock_factory.current_user = CurrentUser(
            user_id=TEST_USER_ID, email="test@example.com"
        )

        # Act
        with patch(
            "swen.application.integration.commands."
            "create_external_account_command.ExternalAccountManagementService",
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            command = CreateExternalAccountCommand.from_factory(mock_factory)

        # Assert
        assert isinstance(command, CreateExternalAccountCommand)
        assert command._management_service is mock_service
        mock_service_class.assert_called_once_with(
            account_repository=mock_factory.account_repository.return_value,
            mapping_repository=mock_factory.account_mapping_repository.return_value,
            transaction_repository=mock_factory.transaction_repository.return_value,
            current_user=mock_factory.current_user,
        )


class TestCreateExternalAccountCommandDTOMapping:
    """Test DTO mapping edge cases."""

    @pytest.mark.asyncio
    async def test_handles_null_created_at(self):
        """Test that DTO mapping handles None created_at gracefully."""
        command, mgmt_service, _, _ = _make_command()

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "Test"
        mock_account.account_number = "EXT-12345678"

        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "Test"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = None  # None created_at

        mgmt_service.create_or_find_external_account.return_value = (
            ExternalAccountResult(
                account=mock_account,
                mapping=mock_mapping,
                transactions_reconciled=0,
                already_existed=True,
            )
        )

        result = await command.execute(
            iban=TEST_IBAN,
            name="Test",
            currency="EUR",
            account_type=AccountType.ASSET,
            reconcile=False,
        )

        assert result.mapping.created_at is None

    @pytest.mark.asyncio
    async def test_handles_different_currencies(self):
        """Test that different currencies are passed through correctly."""
        command, mgmt_service, _, _ = _make_command()

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.name = "US Account"
        mock_account.account_number = "EXT-12345678"
        mock_mapping = MagicMock()
        mock_mapping.id = uuid4()
        mock_mapping.iban = TEST_IBAN
        mock_mapping.account_name = "US Account"
        mock_mapping.accounting_account_id = mock_account.id
        mock_mapping.created_at = MagicMock()
        mock_mapping.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"

        mgmt_service.create_or_find_external_account.return_value = (
            ExternalAccountResult(
                account=mock_account,
                mapping=mock_mapping,
                transactions_reconciled=0,
                already_existed=False,
            )
        )

        await command.execute(
            iban=TEST_IBAN,
            name="US Account",
            currency="USD",
            account_type=AccountType.ASSET,
            reconcile=False,
        )

        call_args = mgmt_service.create_or_find_external_account.call_args
        assert call_args.kwargs["currency"] == Currency("USD")
