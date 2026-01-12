"""
Unit tests for TransactionImportRepositorySQLAlchemy.

Tests the persistence of transaction import records that track bank transaction imports.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.value_objects import ImportStatus
from swen.infrastructure.persistence.sqlalchemy.models.banking import (
    BankAccountModel,
    BankTransactionModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    TransactionImportModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    TransactionImportRepositorySQLAlchemy,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tests.unit.infrastructure.persistence.conftest import TEST_USER_ID


# Module-level list to store pre-created bank transaction IDs for each test
_bank_tx_ids: list[UUID] = []
_tx_id_counter = 0


def _get_next_bank_tx_id():
    """Get the next available bank transaction ID from the pre-created pool."""
    global _tx_id_counter
    if _tx_id_counter >= len(_bank_tx_ids):
        _tx_id_counter = 0  # Reset if we run out
    tx_id = _bank_tx_ids[_tx_id_counter]
    _tx_id_counter += 1
    return tx_id


@pytest_asyncio.fixture(autouse=True)
async def setup_bank_transactions(async_session):
    """Create bank account and transactions needed for TransactionImport tests."""
    global _bank_tx_ids, _tx_id_counter
    _tx_id_counter = 0
    _bank_tx_ids = []

    # Create a bank account for FK satisfaction
    bank_account = BankAccountModel(
        user_id=TEST_USER_ID,
        iban="DE99999999999999999999",
        account_number="9999999999",
        blz="99999999",
        owner_name="Import Test User",
        currency="EUR",
    )
    async_session.add(bank_account)
    await async_session.flush()

    # Create 20 bank transactions for FK satisfaction
    today = datetime.now(tz=timezone.utc).date()
    for i in range(20):
        tx = BankTransactionModel(
            account_id=bank_account.id,
            booking_date=today,
            value_date=today,
            amount=Decimal("100.00"),
            currency="EUR",
            purpose=f"Import test transaction {i + 1}",
            identity_hash=f"import_test_hash_{uuid4().hex[:8]}",
            hash_sequence=i + 1,
        )
        async_session.add(tx)
        await async_session.flush()
        _bank_tx_ids.append(tx.id)

    await async_session.commit()
    yield
    # Cleanup happens automatically via transaction rollback


# Helper function to create test import
def create_test_import(**overrides) -> TransactionImport:
    """Create a test transaction import with default values.

    Uses pre-created bank transaction IDs from the fixture.
    """
    defaults = {
        "bank_transaction_id": _get_next_bank_tx_id(),
        "status": ImportStatus.PENDING,
        "accounting_transaction_id": None,
        "error_message": None,
        "user_id": TEST_USER_ID,
    }
    defaults.update(overrides)
    return TransactionImport(**defaults)


@pytest.mark.asyncio
class TestTransactionImportRepositorySQLAlchemy:
    """Test suite for TransactionImportRepositorySQLAlchemy."""

    async def test_save_new_import(self, async_session, user_context):
        """Test saving a new transaction import."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()

        # Act
        await repo.save(transaction_import)
        await async_session.commit()

        # Assert - verify it was saved in database
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.id == transaction_import.id,
        )
        result = await async_session.execute(stmt)
        saved_model = result.scalar_one_or_none()

        assert saved_model is not None
        assert saved_model.id == transaction_import.id
        assert saved_model.bank_transaction_id == transaction_import.bank_transaction_id
        assert saved_model.status == transaction_import.status

    async def test_save_updates_existing_import(self, async_session, user_context):
        """Test that saving an existing import updates it."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()
        await repo.save(transaction_import)
        await async_session.commit()

        # Act - mark as imported
        accounting_txn_id = uuid4()
        transaction_import.mark_as_imported(accounting_txn_id)
        await repo.save(transaction_import)
        await async_session.commit()

        # Assert
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.id == transaction_import.id,
        )
        result = await async_session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        assert updated_model is not None
        assert updated_model.status == ImportStatus.SUCCESS
        assert updated_model.accounting_transaction_id == accounting_txn_id

    async def test_find_by_id(self, async_session, user_context):
        """Test finding an import by ID."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()
        await repo.save(transaction_import)
        await async_session.commit()

        # Act
        found_import = await repo.find_by_id(transaction_import.id)

        # Assert
        assert found_import is not None
        assert found_import.id == transaction_import.id
        assert (
            found_import.bank_transaction_id == transaction_import.bank_transaction_id
        )

    async def test_find_by_id_returns_none_when_not_found(
        self, async_session, user_context
    ):
        """Test that find_by_id returns None for non-existent import."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        non_existent_id = uuid4()

        # Act
        found_import = await repo.find_by_id(non_existent_id)

        # Assert
        assert found_import is None

    async def test_find_by_accounting_transaction_id(self, async_session, user_context):
        """Test finding import by accounting transaction ID."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        accounting_txn_id = uuid4()
        transaction_import = create_test_import(
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=accounting_txn_id,
        )
        await repo.save(transaction_import)
        await async_session.commit()

        # Act
        found_import = await repo.find_by_accounting_transaction_id(accounting_txn_id)

        # Assert
        assert found_import is not None
        assert found_import.accounting_transaction_id == accounting_txn_id

    async def test_find_by_status(self, async_session, user_context):
        """Test finding all imports with a specific status."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)

        import1 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        import2 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        import3 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.FAILED,
            error_message="Test error",
        )

        await repo.save(import1)
        await repo.save(import2)
        await repo.save(import3)
        await async_session.commit()

        # Act
        success_imports = await repo.find_by_status(ImportStatus.SUCCESS)
        failed_imports = await repo.find_by_status(ImportStatus.FAILED)

        # Assert
        assert len(success_imports) == 2
        assert len(failed_imports) == 1
        assert all(i.status == ImportStatus.SUCCESS for i in success_imports)

    async def test_find_failed_imports(self, async_session, user_context):
        """Test finding all failed imports."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)

        # Create failed import
        failed_import = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.FAILED,
            error_message="Test error",
        )
        await repo.save(failed_import)

        # Create success import
        success_import = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        await repo.save(success_import)
        await async_session.commit()

        # Act
        failed_imports = await repo.find_failed_imports()

        # Assert
        assert len(failed_imports) == 1
        assert failed_imports[0].status == ImportStatus.FAILED

    async def test_find_failed_imports_with_date_filter(
        self, async_session, user_context
    ):
        """Test finding failed imports since a specific date."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=7)

        failed_import = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.FAILED,
            error_message="Recent error",
        )
        await repo.save(failed_import)
        await async_session.commit()

        # Act
        recent_failed = await repo.find_failed_imports(since=cutoff_date)

        # Assert
        assert len(recent_failed) >= 1

    async def test_count_by_status(self, async_session, user_context):
        """Test counting imports by status."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)

        import1 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        import2 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        import3 = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.FAILED,
            error_message="Test error",
        )

        await repo.save(import1)
        await repo.save(import2)
        await repo.save(import3)
        await async_session.commit()

        # Act
        counts = await repo.count_by_status()

        # Assert
        assert counts.get("success", 0) == 2
        assert counts.get("failed", 0) == 1

    async def test_delete_import(self, async_session, user_context):
        """Test deleting an import record."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()
        await repo.save(transaction_import)
        await async_session.commit()

        # Act
        deleted = await repo.delete(transaction_import.id)
        await async_session.commit()

        # Assert
        assert deleted is True

        # Verify it's gone from database
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.id == transaction_import.id,
        )
        result = await async_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_import_returns_false(
        self, async_session, user_context
    ):
        """Test that deleting a non-existent import returns False."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        non_existent_id = uuid4()

        # Act
        deleted = await repo.delete(non_existent_id)

        # Assert
        assert deleted is False

    async def test_domain_to_model_mapping_preserves_all_fields(
        self, async_session, user_context
    ):
        """Test that all domain fields are correctly mapped to model and back."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        accounting_txn_id = uuid4()
        transaction_import = create_test_import(
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=accounting_txn_id,
        )

        # Act - save and retrieve
        await repo.save(transaction_import)
        await async_session.commit()
        retrieved_import = await repo.find_by_id(transaction_import.id)

        # Assert - all fields preserved
        assert retrieved_import is not None
        assert retrieved_import.id == transaction_import.id
        assert (
            retrieved_import.bank_transaction_id
            == transaction_import.bank_transaction_id
        )
        assert retrieved_import.status == transaction_import.status
        assert retrieved_import.accounting_transaction_id == accounting_txn_id
        assert retrieved_import.created_at.replace(
            tzinfo=None,
        ) == transaction_import.created_at.replace(tzinfo=None)

    async def test_mark_as_duplicate(self, async_session, user_context):
        """Test marking an import as duplicate."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()
        await repo.save(transaction_import)
        await async_session.commit()

        # Act
        transaction_import.mark_as_duplicate()
        await repo.save(transaction_import)
        await async_session.commit()

        # Assert
        retrieved = await repo.find_by_id(transaction_import.id)
        assert retrieved is not None
        assert retrieved.status == ImportStatus.DUPLICATE

    async def test_mark_as_skipped(self, async_session, user_context):
        """Test marking an import as skipped."""
        # Arrange
        repo = TransactionImportRepositorySQLAlchemy(async_session, user_context)
        transaction_import = create_test_import()
        await repo.save(transaction_import)
        await async_session.commit()

        # Act
        transaction_import.mark_as_skipped("No account mapping found")
        await repo.save(transaction_import)
        await async_session.commit()

        # Assert
        retrieved = await repo.find_by_id(transaction_import.id)
        assert retrieved is not None
        assert retrieved.status == ImportStatus.SKIPPED
        assert retrieved.error_message == "No account mapping found"

    async def test_database_constraint_prevents_success_without_transaction_id(
        self,
        async_session,
    ):
        """Test that database constraint prevents SUCCESS without transaction ID."""
        # Arrange - try to create a model directly that violates the constraint
        invalid_model = TransactionImportModel(
            id=uuid4(),
            user_id=TEST_USER_ID,
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=None,  # This violates the constraint!
        )

        # Act & Assert
        async_session.add(invalid_model)
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.commit()  # Constraint checked on commit, not flush

        assert "check_success_has_transaction_id" in str(exc_info.value)

    async def test_database_constraint_prevents_failed_without_error_message(
        self,
        async_session,
    ):
        """Test that database constraint prevents FAILED without error message."""
        # Arrange - try to create a model directly that violates the constraint
        invalid_model = TransactionImportModel(
            id=uuid4(),
            user_id=TEST_USER_ID,
            bank_transaction_id=_get_next_bank_tx_id(),
            status=ImportStatus.FAILED,
            error_message=None,  # This violates the constraint!
        )

        # Act & Assert
        async_session.add(invalid_model)
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.commit()  # Constraint checked on commit, not flush

        assert "check_failed_has_error_message" in str(exc_info.value)
