"""
Tests for handling duplicate/identical bank transactions.

This test module specifically tests the scenario where the bank returns
multiple transactions with identical content (e.g., two refunds of €3.10
on the same day from the same merchant with the same purpose).

The hash + sequence deduplication strategy ensures:
1. Each identical transaction gets a unique sequence number (1, 2, 3...)
2. Re-importing the same batch doesn't create duplicates
3. All transactions are properly imported to accounting
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from swen.application.factories import BankImportTransactionFactory
from swen.application.services import TransactionImportService
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import ImportStatus, ResolutionResult
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_transaction_repository import (
    StoredBankTransaction,
)
from swen.application.ports.identity import CurrentUser

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def create_hostelworld_refund() -> BankTransaction:
    """Create a transaction matching the real Hostelworld refund scenario."""
    return BankTransaction(
        booking_date=date(2025, 11, 10),
        value_date=date(2025, 11, 10),
        amount=Decimal("3.10"),
        currency="EUR",
        purpose="20251110125940 WWW.HOSTELWORLD.COM IE",
        applicant_name="WWW.HOSTELWORLD.COM/DUBLIN",
        applicant_iban=None,
        bank_reference="STARTUMS",  # Same reference for both transactions!
    )


def create_stored_transaction(
    transaction: BankTransaction,
    hash_sequence: int,
    is_new: bool = True,
) -> StoredBankTransaction:
    """Create a StoredBankTransaction for testing."""
    identity_hash = transaction.compute_identity_hash("DE89370400440532013000")
    return StoredBankTransaction(
        id=uuid4(),
        identity_hash=identity_hash,
        hash_sequence=hash_sequence,
        transaction=transaction,
        is_imported=False,
        is_new=is_new,
    )


@pytest.fixture
def service_with_mocks():
    """Create a TransactionImportService with mocked dependencies."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    # Setup default account mocks
    asset_account = Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number="1200",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )
    income_account = Account(
        name="Sonstige Einnahmen",
        account_type=AccountType.INCOME,
        account_number="3100",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )

    bank_account_service.get_or_create_asset_account.return_value = asset_account

    # Create a mock resolution result
    resolution_result = MagicMock(spec=ResolutionResult)
    resolution_result.account = income_account
    resolution_result.is_from_ai = False
    resolution_result.has_ai_result = False
    resolution_result.ai_result = None
    counter_account_resolution_service.resolve_counter_account_with_details.return_value = resolution_result

    # No existing imports
    import_repo.find_by_bank_transaction_id.return_value = None

    # Mapping repo returns None (external transaction, not internal transfer)
    mapping_repo.find_by_iban.return_value = None

    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )

    transaction_factory = BankImportTransactionFactory(
        current_user=current_user,
    )

    service = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )

    return service, {
        "bank_account_service": bank_account_service,
        "counter_account_resolution_service": counter_account_resolution_service,
        "account_repo": account_repo,
        "transaction_repo": transaction_repo,
        "mapping_repo": mapping_repo,
        "import_repo": import_repo,
        "asset_account": asset_account,
        "income_account": income_account,
    }


class TestIdenticalTransactionHandling:
    """Tests for handling identical bank transactions."""

    @pytest.mark.asyncio
    async def test_two_identical_transactions_create_two_accounting_entries(
        self,
        service_with_mocks,
    ):
        """
        Two identical Hostelworld refunds should create two accounting entries.

        This is the core test case that was failing before the fix.
        """
        svc, deps = service_with_mocks

        # Create two identical transactions with different sequence numbers
        transaction = create_hostelworld_refund()
        stored1 = create_stored_transaction(transaction, hash_sequence=1)
        stored2 = create_stored_transaction(transaction, hash_sequence=2)

        # Import both
        results = await svc.import_from_stored_transactions(
            stored_transactions=[stored1, stored2],
            source_iban="DE89370400440532013000",
            auto_post=False,
        )

        # Both should be successful
        assert len(results) == 2
        assert all(r.status == ImportStatus.SUCCESS for r in results)

        # Both should have created accounting transactions
        assert deps["transaction_repo"].save.await_count == 2

        # Both should have created import records
        assert deps["import_repo"].save.await_count == 2

    @pytest.mark.asyncio
    async def test_import_uses_bank_transaction_id_for_deduplication(
        self,
        service_with_mocks,
    ):
        """Import should use bank_transaction_id, not hash-based identity."""
        svc, deps = service_with_mocks

        transaction = create_hostelworld_refund()
        stored = create_stored_transaction(transaction, hash_sequence=1)

        await svc.import_from_stored_transactions(
            stored_transactions=[stored],
            source_iban="DE89370400440532013000",
            auto_post=False,
        )

        # Should check by bank_transaction_id, not by identity hash
        deps["import_repo"].find_by_bank_transaction_id.assert_awaited_once_with(
            stored.id,
        )
        # Should NOT use the old hash-based lookup
        deps["import_repo"].find_by_bank_transaction_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_imported_transaction_returns_duplicate(
        self,
        service_with_mocks,
    ):
        """Re-importing an already imported transaction should return DUPLICATE."""
        svc, deps = service_with_mocks

        transaction = create_hostelworld_refund()
        stored = create_stored_transaction(transaction, hash_sequence=1)

        # Simulate existing import record
        existing_import = MagicMock()
        existing_import.status = ImportStatus.SUCCESS
        deps["import_repo"].find_by_bank_transaction_id.return_value = existing_import

        results = await svc.import_from_stored_transactions(
            stored_transactions=[stored],
            source_iban="DE89370400440532013000",
            auto_post=False,
        )

        assert len(results) == 1
        assert results[0].status == ImportStatus.DUPLICATE
        assert "already imported" in results[0].error_message.lower()

        # Should NOT create accounting transaction
        deps["transaction_repo"].save.assert_not_called()

    @pytest.mark.asyncio
    async def test_stored_transaction_gets_bank_transaction_id_in_import_record(
        self,
        service_with_mocks,
    ):
        """Import record should reference bank_transaction_id."""
        svc, deps = service_with_mocks

        transaction = create_hostelworld_refund()
        stored = create_stored_transaction(transaction, hash_sequence=1)

        await svc.import_from_stored_transactions(
            stored_transactions=[stored],
            source_iban="DE89370400440532013000",
            auto_post=False,
        )

        # Check the saved import record
        saved_import = deps["import_repo"].save.await_args.args[0]
        assert saved_import.bank_transaction_id == stored.id


class TestSequenceNumberAssignment:
    """Tests for identity hash and sequence number handling."""

    @pytest.mark.asyncio
    async def test_identical_transactions_have_same_hash_different_sequences(
        self,
        service_with_mocks,
    ):
        """Identical transactions should have same hash but different sequences."""
        transaction = create_hostelworld_refund()

        stored1 = create_stored_transaction(transaction, hash_sequence=1)
        stored2 = create_stored_transaction(transaction, hash_sequence=2)

        # Same hash
        assert stored1.identity_hash == stored2.identity_hash

        # Different sequence numbers
        assert stored1.hash_sequence != stored2.hash_sequence

        # Different UUIDs
        assert stored1.id != stored2.id

    @pytest.mark.asyncio
    async def test_different_transactions_have_different_hashes(
        self,
        service_with_mocks,
    ):
        """Different transactions should have different hashes."""
        transaction1 = create_hostelworld_refund()
        transaction2 = BankTransaction(
            booking_date=date(2025, 11, 10),
            value_date=date(2025, 11, 10),
            amount=Decimal("5.00"),  # Different amount
            currency="EUR",
            purpose="Different transaction",
            applicant_name="Someone Else",
        )

        stored1 = create_stored_transaction(transaction1, hash_sequence=1)
        stored2 = create_stored_transaction(transaction2, hash_sequence=1)

        # Different hashes
        assert stored1.identity_hash != stored2.identity_hash


class TestAutoPostBehavior:
    """Tests for auto-post functionality."""

    @pytest.mark.asyncio
    async def test_auto_post_posts_transactions(
        self,
        service_with_mocks,
    ):
        """auto_post=True should post the transactions."""
        svc, deps = service_with_mocks

        transaction = create_hostelworld_refund()
        stored = create_stored_transaction(transaction, hash_sequence=1)

        results = await svc.import_from_stored_transactions(
            stored_transactions=[stored],
            source_iban="DE89370400440532013000",
            auto_post=True,
        )

        assert results[0].status == ImportStatus.SUCCESS
        # The accounting transaction should be posted
        saved_tx = results[0].accounting_transaction
        assert saved_tx is not None
        assert saved_tx.is_posted
