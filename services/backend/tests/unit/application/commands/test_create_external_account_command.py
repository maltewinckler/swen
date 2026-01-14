"""Unit tests for CreateExternalAccountCommand."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from swen.application.commands.integration import (
    CreateExternalAccountCommand,
    CreateExternalAccountResult,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError, InvalidCurrencyError
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping
from swen.application.ports.identity import CurrentUser

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_IBAN = "DE51120700700756557355"


def _make_command():
    """Create command with mocked repositories."""
    account_repo = AsyncMock()
    mapping_repo = AsyncMock()
    transaction_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    command = CreateExternalAccountCommand(
        account_repository=account_repo,
        mapping_repository=mapping_repo,
        transaction_repository=transaction_repo,
        current_user=current_user,
    )

    return command, account_repo, mapping_repo, transaction_repo


class TestCreateExternalAccountCommand:
    """Test cases for CreateExternalAccountCommand."""

    @pytest.mark.asyncio
    async def test_creates_new_account_and_mapping(self):
        """Test creating a new external account creates both account and mapping."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service to not reconcile anything
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 0
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="Deutsche Bank Depot",
                currency="EUR",
                reconcile=True,
            )

        # Assert
        assert isinstance(result, CreateExternalAccountResult)
        assert result.already_existed is False
        assert result.transactions_reconciled == 0

        # Check account was created correctly
        assert result.account.name == "Deutsche Bank Depot"
        assert result.account.account_type == AccountType.ASSET
        assert result.account.account_number == f"EXT-{TEST_IBAN[-8:]}"
        assert result.account.iban == TEST_IBAN
        assert result.account.default_currency == Currency("EUR")
        assert result.account.user_id == TEST_USER_ID

        # Check mapping was created correctly
        assert result.mapping.iban == TEST_IBAN
        assert result.mapping.account_name == "Deutsche Bank Depot"
        assert result.mapping.accounting_account_id == result.account.id
        assert result.mapping.user_id == TEST_USER_ID
        assert result.mapping.is_active is True

        # Verify repositories were called
        account_repo.save.assert_called_once()
        mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_existing_when_mapping_exists(self):
        """Test that existing mapping is returned without creating new one."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # Create existing account and mapping
        existing_account = Account(
            name="Existing Depot",
            account_type=AccountType.ASSET,
            account_number=TEST_IBAN,
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )
        existing_mapping = AccountMapping(
            iban=TEST_IBAN,
            accounting_account_id=existing_account.id,
            account_name="Existing Depot",
            user_id=TEST_USER_ID,
        )

        mapping_repo.find_by_iban.return_value = existing_mapping
        account_repo.find_by_id.return_value = existing_account

        # Act
        result = await command.execute(
            iban=TEST_IBAN,
            name="Deutsche Bank Depot",  # Different name - should be ignored
            currency="EUR",
            reconcile=True,
        )

        # Assert
        assert result.already_existed is True
        assert result.transactions_reconciled == 0
        assert result.account.name == "Existing Depot"  # Original name kept
        assert result.mapping.iban == TEST_IBAN

        # Verify no saves were called
        account_repo.save.assert_not_called()
        mapping_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconciles_existing_transactions(self):
        """Test that existing transactions are reconciled when reconcile=True."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service to reconcile some transactions
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 5  # 5 reconciled
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="Deutsche Bank Depot",
                currency="EUR",
                reconcile=True,
            )

            # Assert
            assert result.transactions_reconciled == 5
            mock_service.reconcile_for_new_account.assert_called_once()
            call_args = mock_service.reconcile_for_new_account.call_args
            assert call_args.kwargs["iban"] == TEST_IBAN

    @pytest.mark.asyncio
    async def test_skips_reconciliation_when_disabled(self):
        """Test that reconciliation is skipped when reconcile=False."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="Deutsche Bank Depot",
                currency="EUR",
                reconcile=False,  # Disabled
            )

            # Assert
            assert result.transactions_reconciled == 0
            mock_service.reconcile_for_new_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_normalizes_iban(self):
        """Test that IBAN is normalized (uppercase, stripped)."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 0
            mock_service_class.return_value = mock_service

            # Act - lowercase and with whitespace
            result = await command.execute(
                iban="  de51120700700756557355  ",
                name="Test Account",
                currency="EUR",
                reconcile=False,
            )

        # Assert - IBAN should be normalized
        assert result.account.iban == "DE51120700700756557355"
        assert result.account.account_number == "EXT-56557355"
        assert result.mapping.iban == "DE51120700700756557355"

    @pytest.mark.asyncio
    async def test_validates_currency(self):
        """Test that invalid currency raises InvalidCurrencyError."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping
        mapping_repo.find_by_iban.return_value = None

        # Act & Assert - "XYZ" is a valid format but unsupported currency
        with pytest.raises(InvalidCurrencyError, match="Invalid currency 'XYZ'"):
            await command.execute(
                iban=TEST_IBAN,
                name="Test Account",
                currency="XYZ",
                reconcile=False,
            )

    @pytest.mark.asyncio
    async def test_raises_when_mapping_exists_but_account_missing(self):
        """Test error when mapping exists but referenced account doesn't."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # Orphaned mapping - account was deleted
        orphaned_mapping = AccountMapping(
            iban=TEST_IBAN,
            accounting_account_id=uuid4(),  # Non-existent account
            account_name="Orphaned Mapping",
            user_id=TEST_USER_ID,
        )

        mapping_repo.find_by_iban.return_value = orphaned_mapping
        account_repo.find_by_id.return_value = None  # Account not found

        # Act & Assert
        with pytest.raises(AccountNotFoundError, match="not found"):
            await command.execute(
                iban=TEST_IBAN,
                name="Test Account",
                currency="EUR",
                reconcile=False,
            )

    @pytest.mark.asyncio
    async def test_supports_different_currencies(self):
        """Test creating accounts with different currencies."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 0
            mock_service_class.return_value = mock_service

            # Act - Create USD account
            result = await command.execute(
                iban="US12345678901234567890",  # Made-up IBAN for test
                name="US Stock Portfolio",
                currency="USD",
                reconcile=False,
            )

        # Assert
        assert result.account.default_currency == Currency("USD")


class TestCreateExternalAccountCommandLiability:
    """Test cases for creating LIABILITY accounts (credit cards, loans)."""

    @pytest.mark.asyncio
    async def test_creates_liability_account_with_lia_prefix(self):
        """Test creating a liability account uses LIA- prefix instead of EXT-."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_liability_for_new_account.return_value = 0
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="Norwegian VISA",
                currency="EUR",
                account_type=AccountType.LIABILITY,
                reconcile=True,
            )

        # Assert
        assert result.account.account_type == AccountType.LIABILITY
        assert result.account.account_number == f"LIA-{TEST_IBAN[-8:]}"
        assert result.account.name == "Norwegian VISA"

    @pytest.mark.asyncio
    async def test_liability_reconciliation_called_for_liability_accounts(self):
        """Test that liability reconciliation is called for LIABILITY accounts."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_liability_for_new_account.return_value = 3
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="Credit Card",
                currency="EUR",
                account_type=AccountType.LIABILITY,
                reconcile=True,
            )

            # Assert
            assert result.transactions_reconciled == 3
            mock_service.reconcile_liability_for_new_account.assert_called_once()
            mock_service.reconcile_for_new_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_asset_reconciliation_called_for_asset_accounts(self):
        """Test that asset reconciliation is called for ASSET accounts (not liability)."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping or account
        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 2
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="External Bank",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

            # Assert
            assert result.transactions_reconciled == 2
            mock_service.reconcile_for_new_account.assert_called_once()
            mock_service.reconcile_liability_for_new_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_invalid_account_types(self):
        """Test that only ASSET and LIABILITY account types are allowed."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping
        mapping_repo.find_by_iban.return_value = None

        from swen.domain.shared.exceptions import ValidationError

        # Act & Assert - EXPENSE is not allowed
        with pytest.raises(ValidationError, match="ASSET or LIABILITY"):
            await command.execute(
                iban=TEST_IBAN,
                name="Invalid",
                currency="EUR",
                account_type=AccountType.EXPENSE,
                reconcile=False,
            )


class TestCreateExternalAccountCommandReuseExisting:
    """Test cases for reusing existing accounts by IBAN."""

    @pytest.mark.asyncio
    async def test_reuses_existing_account_by_iban_creates_mapping(self):
        """Test that existing account by IBAN is reused when no mapping exists."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping, but account exists
        existing_account = Account(
            name="Existing Account",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER_ID,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_account
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_for_new_account.return_value = 2
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="New Name",  # Different name than existing account
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

        # Assert
        assert result.already_existed is True  # Account existed
        assert result.account.id == existing_account.id  # Reused existing
        assert result.account.name == "Existing Account"  # Original name kept
        assert result.mapping.iban == TEST_IBAN
        assert result.mapping.accounting_account_id == existing_account.id
        assert result.mapping.account_name == "New Name"  # Mapping gets new name
        assert result.transactions_reconciled == 2

        # Account was NOT saved (reused), only mapping
        account_repo.save.assert_not_called()
        mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_reuses_existing_liability_account_by_iban(self):
        """Test that existing LIABILITY account by IBAN is reused."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping, but LIABILITY account exists
        existing_liability = Account(
            name="Existing Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-existing",
            user_id=TEST_USER_ID,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_liability
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.reconcile_liability_for_new_account.return_value = 1
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="VISA Card",
                currency="EUR",
                account_type=AccountType.LIABILITY,
                reconcile=True,
            )

        # Assert
        assert result.already_existed is True
        assert result.account.id == existing_liability.id
        assert result.account.account_type == AccountType.LIABILITY
        assert result.transactions_reconciled == 1
        mock_service.reconcile_liability_for_new_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_existing_account_type_mismatch(self):
        """Test error when existing account has different type than requested."""
        from swen.domain.shared.exceptions import ValidationError

        command, account_repo, mapping_repo, transaction_repo = _make_command()

        # No existing mapping, but ASSET account exists
        existing_asset = Account(
            name="Existing Asset",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER_ID,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_asset

        # Act & Assert - Try to create LIABILITY for IBAN that has ASSET
        with pytest.raises(ValidationError, match="asset.*not liability"):
            await command.execute(
                iban=TEST_IBAN,
                name="Credit Card",
                currency="EUR",
                account_type=AccountType.LIABILITY,  # Mismatch!
                reconcile=False,
            )

    @pytest.mark.asyncio
    async def test_reuse_skips_reconciliation_when_disabled(self):
        """Test that reconciliation is skipped when reusing account with reconcile=False."""
        command, account_repo, mapping_repo, transaction_repo = _make_command()

        existing_account = Account(
            name="Existing Account",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER_ID,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_account
        mapping_repo.save = AsyncMock()

        # Mock reconciliation service
        with patch(
            "swen.application.commands.integration.create_external_account_command.TransferReconciliationService",
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Act
            result = await command.execute(
                iban=TEST_IBAN,
                name="New Name",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=False,  # Disabled
            )

        # Assert
        assert result.already_existed is True
        assert result.transactions_reconciled == 0
        mock_service.reconcile_for_new_account.assert_not_called()


class TestCreateExternalAccountCommandFromFactory:
    """Test the from_factory class method."""

    def test_from_factory_creates_command(self):
        """Test that from_factory correctly creates command from factory."""
        # Create mock factory
        mock_factory = Mock()
        mock_factory.account_repository.return_value = AsyncMock()
        mock_factory.account_mapping_repository.return_value = AsyncMock()
        mock_factory.transaction_repository.return_value = AsyncMock()
        mock_factory.current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

        # Act
        command = CreateExternalAccountCommand.from_factory(mock_factory)

        # Assert
        assert isinstance(command, CreateExternalAccountCommand)
        mock_factory.account_repository.assert_called_once()
        mock_factory.account_mapping_repository.assert_called_once()
        mock_factory.transaction_repository.assert_called_once()
