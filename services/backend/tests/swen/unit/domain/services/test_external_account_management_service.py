"""Unit tests for ExternalAccountManagementService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.exceptions import InvalidIbanError
from swen.domain.integration.services import ExternalAccountManagementService
from swen.domain.integration.services.external_account_management_service import (
    ExternalAccountResult,
)
from swen.domain.shared.current_user import CurrentUser
from swen.domain.shared.exceptions import ValidationError

# Test user for all tests
TEST_USER = CurrentUser(user_id=uuid4(), email="test@example.com")
TEST_IBAN = "DE51120700700756557355"


def _make_service(
    account_repo: AsyncMock | None = None,
    mapping_repo: AsyncMock | None = None,
    transaction_repo: AsyncMock | None = None,
) -> tuple[ExternalAccountManagementService, AsyncMock, AsyncMock, AsyncMock]:
    """Create a service instance with mocked repositories."""
    if account_repo is None:
        account_repo = AsyncMock()
    if mapping_repo is None:
        mapping_repo = AsyncMock()
    if transaction_repo is None:
        transaction_repo = AsyncMock()

    service = ExternalAccountManagementService(
        account_repository=account_repo,
        mapping_repository=mapping_repo,
        transaction_repository=transaction_repo,
        current_user=TEST_USER,
    )
    return service, account_repo, mapping_repo, transaction_repo


class TestGenerateAccountNumber:
    """Tests for account number generation."""

    def test_generates_ext_prefix_for_asset(self):
        """Test ASSET accounts get EXT- prefix."""
        service, _, _, _ = _make_service()
        result = service.generate_account_number(TEST_IBAN, AccountType.ASSET)
        assert result == f"EXT-{TEST_IBAN[-8:]}"

    def test_generates_lia_prefix_for_liability(self):
        """Test LIABILITY accounts get LIA- prefix."""
        service, _, _, _ = _make_service()
        result = service.generate_account_number(TEST_IBAN, AccountType.LIABILITY)
        assert result == f"LIA-{TEST_IBAN[-8:]}"


class TestCreateOrFindExternalAccount:
    """Tests for the main business method."""

    @pytest.mark.asyncio
    async def test_returns_existing_when_mapping_exists(self):
        """Test that existing mapping returns existing account and mapping."""
        service, account_repo, mapping_repo, _ = _make_service()

        account = Account(
            name="Existing Depot",
            account_type=AccountType.ASSET,
            account_number="EXT-56557355",
            user_id=TEST_USER.user_id,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )
        mapping = AccountMapping(
            iban=TEST_IBAN,
            accounting_account_id=account.id,
            account_name="Existing Depot",
            user_id=TEST_USER.user_id,
        )

        mapping_repo.find_by_iban.return_value = mapping
        account_repo.find_by_id.return_value = account

        result = await service.create_or_find_external_account(
            iban=TEST_IBAN,
            name="Different Name",
            currency="EUR",
            account_type=AccountType.ASSET,
            reconcile=True,
        )

        assert result.already_existed is True
        assert result.transactions_reconciled == 0
        assert result.account.id == account.id
        assert result.mapping.id == mapping.id
        account_repo.save.assert_not_called()
        mapping_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_mapping_exists_but_account_missing(self):
        """Test error when mapping exists but referenced account was deleted."""
        service, account_repo, mapping_repo, _ = _make_service()

        orphaned_mapping = AccountMapping(
            iban=TEST_IBAN,
            accounting_account_id=uuid4(),
            account_name="Orphaned",
            user_id=TEST_USER.user_id,
        )
        mapping_repo.find_by_iban.return_value = orphaned_mapping
        account_repo.find_by_id.return_value = None

        with pytest.raises(AccountNotFoundError):
            await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="Test",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=False,
            )

    @pytest.mark.asyncio
    async def test_creates_mapping_when_account_exists(self):
        """Test that existing account by IBAN triggers mapping creation only."""
        service, account_repo, mapping_repo, _ = _make_service()

        existing_account = Account(
            name="Existing Account",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER.user_id,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_account
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        mock_recon_service = AsyncMock()
        mock_recon_service.reconcile_for_new_account.return_value = 2

        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="New Name",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

        assert result.already_existed is True
        assert result.transactions_reconciled == 2
        account_repo.save.assert_not_called()
        mapping_repo.save.assert_called_once()
        mock_recon_service.reconcile_for_new_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_both_when_nothing_exists(self):
        """Test that completely new IBAN creates both account and mapping."""
        service, account_repo, mapping_repo, _ = _make_service()

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        mock_recon_service = AsyncMock()
        mock_recon_service.reconcile_for_new_account.return_value = 3

        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="New External Account",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

        assert result.already_existed is False
        assert result.transactions_reconciled == 3
        account_repo.save.assert_called_once()
        mapping_repo.save.assert_called_once()
        mock_recon_service.reconcile_for_new_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_account_type(self):
        """Test that non-ASSET/LIABILITY types are rejected."""
        service, _, _, _ = _make_service()

        with pytest.raises(ValidationError, match="ASSET or LIABILITY"):
            await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="Test",
                currency="EUR",
                account_type=AccountType.EXPENSE,
                reconcile=False,
            )

    @pytest.mark.asyncio
    async def test_raises_on_empty_iban(self):
        """Test that empty IBAN raises InvalidIbanError."""
        service, _, _, _ = _make_service()

        with pytest.raises(InvalidIbanError, match="IBAN cannot be empty"):
            await service.create_or_find_external_account(
                iban="",
                name="Test",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=False,
            )


class TestExternalAccountManagementServiceIntegration:
    """Integration-style tests that verify the full flow with mocked reconciliation."""

    @pytest.mark.asyncio
    async def test_full_flow_creates_new_account_mapping_and_reconciles(self):
        """Test complete flow: create new account, mapping, and reconcile."""
        service, account_repo, mapping_repo, _ = _make_service()

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        # Create a mock reconciliation service
        mock_recon_service = AsyncMock()
        mock_recon_service.reconcile_for_new_account.return_value = 3

        # Patch the TransferReconciliationService creation
        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="New External Account",
                currency="USD",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

        # Assert result structure
        assert isinstance(result, ExternalAccountResult)
        assert result.already_existed is False
        assert result.transactions_reconciled == 3
        assert result.account.iban == TEST_IBAN
        assert result.account.name == "New External Account"
        assert result.account.default_currency == Currency("USD")
        assert result.mapping.iban == TEST_IBAN
        assert result.mapping.accounting_account_id == result.account.id

        # Verify repositories were called
        account_repo.save.assert_called_once()
        mapping_repo.save.assert_called_once()

        # Verify account number generation
        saved_account = account_repo.save.call_args[0][0]
        assert saved_account.account_number == f"EXT-{TEST_IBAN[-8:]}"

    @pytest.mark.asyncio
    async def test_full_flow_liability_reconciliation(self):
        """Test that LIABILITY accounts use liability reconciliation."""
        service, account_repo, mapping_repo, _ = _make_service()

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        mock_recon_service = AsyncMock()
        mock_recon_service.reconcile_liability_for_new_account.return_value = 1

        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="Credit Card",
                currency="EUR",
                account_type=AccountType.LIABILITY,
                reconcile=True,
            )

        assert result.already_existed is False
        assert result.transactions_reconciled == 1
        saved_account = account_repo.save.call_args[0][0]
        assert saved_account.account_number == f"LIA-{TEST_IBAN[-8:]}"

    @pytest.mark.asyncio
    async def test_skips_reconciliation_when_disabled(self):
        """Test that reconciliation is skipped when reconcile=False."""
        service, account_repo, mapping_repo, _ = _make_service()

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = None
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        mock_recon_service = AsyncMock()

        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="Test",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=False,
            )

        assert result.transactions_reconciled == 0
        mock_recon_service.reconcile_for_new_account.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_existing_when_account_exists_creates_mapping(self):
        """Test that existing account by IBAN creates a new mapping."""
        service, account_repo, mapping_repo, _ = _make_service()

        existing_account = Account(
            name="Existing Asset",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER.user_id,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_account
        account_repo.save = AsyncMock()
        mapping_repo.save = AsyncMock()

        mock_recon_service = AsyncMock()
        mock_recon_service.reconcile_for_new_account.return_value = 2

        from unittest.mock import patch

        with patch(
            "swen.domain.integration.services.external_account_management_service.TransferReconciliationService",
            return_value=mock_recon_service,
        ):
            result = await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="New Name",
                currency="EUR",
                account_type=AccountType.ASSET,
                reconcile=True,
            )

        assert result.already_existed is True
        assert result.transactions_reconciled == 2
        # Account was NOT saved (reused)
        account_repo.save.assert_not_called()
        # Mapping WAS saved
        mapping_repo.save.assert_called_once()
        saved_mapping = mapping_repo.save.call_args[0][0]
        assert saved_mapping.accounting_account_id == existing_account.id

    @pytest.mark.asyncio
    async def test_raises_on_account_type_mismatch(self):
        """Test error when existing account has different type than requested."""
        service, account_repo, mapping_repo, _ = _make_service()

        existing_asset = Account(
            name="Asset Account",
            account_type=AccountType.ASSET,
            account_number="EXT-existing",
            user_id=TEST_USER.user_id,
            iban=TEST_IBAN,
            default_currency=Currency("EUR"),
        )

        mapping_repo.find_by_iban.return_value = None
        account_repo.find_by_iban.return_value = existing_asset

        with pytest.raises(ValidationError, match="asset.*not liability"):
            await service.create_or_find_external_account(
                iban=TEST_IBAN,
                name="Credit Card",
                currency="EUR",
                account_type=AccountType.LIABILITY,
                reconcile=False,
            )
