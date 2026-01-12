"""Tests for TransactionImport entity."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.value_objects import ImportStatus

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestTransactionImport:
    """Test cases for TransactionImport entity."""

    def test_transaction_import_creation(self):
        """Test creating a basic TransactionImport instance."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        assert import_record.bank_transaction_id == bank_tx_id
        assert import_record.status == ImportStatus.PENDING
        assert import_record.accounting_transaction_id is None
        assert import_record.error_message is None
        assert isinstance(import_record.id, UUID)
        assert import_record.created_at is not None
        assert import_record.updated_at is not None
        assert import_record.imported_at is None

    def test_transaction_import_with_all_parameters(self):
        """Test creating TransactionImport with all parameters."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=accounting_tx_id,
        )

        assert import_record.status == ImportStatus.SUCCESS
        assert import_record.accounting_transaction_id == accounting_tx_id

    def test_transaction_import_deterministic_id(self):
        """Test same bank transaction ID produces same import record ID."""
        bank_tx_id = uuid4()

        import1 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )
        import2 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )

        # Should have the same ID
        assert import1.id == import2.id

    def test_transaction_import_different_bank_tx_id_different_id(self):
        """Test different bank transaction IDs produce different IDs."""
        bank_tx_id_1 = uuid4()
        bank_tx_id_2 = uuid4()

        import1 = TransactionImport(
            bank_transaction_id=bank_tx_id_1,
            user_id=TEST_USER_ID,
        )
        import2 = TransactionImport(
            bank_transaction_id=bank_tx_id_2,
            user_id=TEST_USER_ID,
        )

        assert import1.id != import2.id

    def test_transaction_import_user_isolation(self):
        """Test same bank transaction ID for different users produces different IDs."""
        bank_tx_id = uuid4()
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        import1 = TransactionImport(bank_transaction_id=bank_tx_id, user_id=user_id_1)
        import2 = TransactionImport(bank_transaction_id=bank_tx_id, user_id=user_id_2)

        assert import1.id != import2.id

    def test_mark_as_imported(self):
        """Test marking import as imported (success)."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_imported(accounting_tx_id)

        assert import_record.status == ImportStatus.SUCCESS
        assert import_record.accounting_transaction_id == accounting_tx_id
        assert import_record.imported_at is not None

    def test_mark_as_imported_clears_previous_error(self):
        """Test successful import clears previous error message."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.FAILED,
            error_message="Previous error",
        )
        import_record.mark_as_imported(accounting_tx_id)

        assert import_record.status == ImportStatus.SUCCESS
        assert import_record.error_message is None

    def test_mark_as_failed(self):
        """Test marking import as failed."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_failed("Connection timeout")

        assert import_record.status == ImportStatus.FAILED
        assert import_record.error_message == "Connection timeout"

    def test_mark_as_failed_empty_message_raises_error(self):
        """Test marking as failed with empty message raises error."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        with pytest.raises(ValueError, match="Error message cannot be empty"):
            import_record.mark_as_failed("")

    def test_mark_as_failed_strips_whitespace(self):
        """Test error message whitespace is stripped."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_failed("  Connection error  ")

        assert import_record.error_message == "Connection error"

    def test_mark_as_duplicate(self):
        """Test marking import as duplicate."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_duplicate()

        assert import_record.status == ImportStatus.DUPLICATE

    def test_mark_as_skipped(self):
        """Test marking import as skipped."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_skipped("Internal transfer")

        assert import_record.status == ImportStatus.SKIPPED
        assert import_record.error_message == "Internal transfer"

    def test_retry_failed_import(self):
        """Test retrying a failed import."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.FAILED,
            error_message="Previous error",
        )
        import_record.retry()

        assert import_record.status == ImportStatus.PENDING
        assert import_record.error_message is None

    def test_retry_skipped_import(self):
        """Test retrying a skipped import."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_skipped("Temporary skip")
        import_record.retry()

        assert import_record.status == ImportStatus.PENDING

    def test_retry_successful_import_raises_error(self):
        """Test retrying successful import raises error."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=accounting_tx_id,
        )

        with pytest.raises(ValueError, match="Cannot retry.*success"):
            import_record.retry()

    def test_is_imported(self):
        """Test is_imported method."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=accounting_tx_id,
        )

        assert import_record.is_imported() is True

    def test_is_failed(self):
        """Test is_failed method."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
            status=ImportStatus.FAILED,
            error_message="Error",
        )

        assert import_record.is_failed() is True

    def test_is_duplicate(self):
        """Test is_duplicate method."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_duplicate()

        assert import_record.is_duplicate() is True

    def test_is_skipped(self):
        """Test is_skipped method."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        import_record.mark_as_skipped("Reason")

        assert import_record.is_skipped() is True

    def test_can_retry(self):
        """Test can_retry for various states."""
        bank_tx_id = uuid4()

        # Pending - cannot retry
        pending = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )
        assert pending.can_retry() is False

        # Failed - can retry
        failed = TransactionImport(
            bank_transaction_id=uuid4(),
            user_id=TEST_USER_ID,
            status=ImportStatus.FAILED,
            error_message="Error",
        )
        assert failed.can_retry() is True

        # Success - cannot retry
        success = TransactionImport(
            bank_transaction_id=uuid4(),
            user_id=TEST_USER_ID,
            status=ImportStatus.SUCCESS,
            accounting_transaction_id=uuid4(),
        )
        assert success.can_retry() is False

    def test_equality(self):
        """Test equality is based on ID."""
        bank_tx_id = uuid4()

        import1 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )
        import2 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )

        # Same ID = equal
        assert import1 == import2

    def test_inequality(self):
        """Test inequality for different IDs."""
        import1 = TransactionImport(bank_transaction_id=uuid4(), user_id=TEST_USER_ID)
        import2 = TransactionImport(bank_transaction_id=uuid4(), user_id=TEST_USER_ID)

        assert import1 != import2

    def test_equality_with_non_transaction_import(self):
        """Test equality with non-TransactionImport returns False."""
        bank_tx_id = uuid4()
        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        assert import_record != "not a TransactionImport"
        assert import_record != 123

    def test_hashable(self):
        """Test TransactionImport is hashable (can be used in sets)."""
        bank_tx_id = uuid4()

        import1 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )
        import2 = TransactionImport(
            bank_transaction_id=bank_tx_id, user_id=TEST_USER_ID
        )

        # Same ID = same hash
        assert hash(import1) == hash(import2)

        # Can be used in set
        imports_set = {import1, import2}
        assert len(imports_set) == 1  # Deduped

    def test_string_representation(self):
        """Test __str__ method."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        str_repr = str(import_record)
        assert "TransactionImport" in str_repr
        assert "pending" in str_repr
        assert str(bank_tx_id) in str_repr

    def test_lifecycle_pending_to_success(self):
        """Test typical success lifecycle."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        assert import_record.status == ImportStatus.PENDING

        import_record.mark_as_imported(accounting_tx_id)
        assert import_record.status == ImportStatus.SUCCESS
        assert import_record.accounting_transaction_id == accounting_tx_id

    def test_lifecycle_pending_to_failed_to_retry_to_success(self):
        """Test retry lifecycle after failure."""
        bank_tx_id = uuid4()
        accounting_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        # Fail
        import_record.mark_as_failed("Database error")
        assert import_record.status == ImportStatus.FAILED

        # Retry
        import_record.retry()
        assert import_record.status == ImportStatus.PENDING

        # Success
        import_record.mark_as_imported(accounting_tx_id)
        assert import_record.status == ImportStatus.SUCCESS

    def test_lifecycle_pending_to_duplicate(self):
        """Test duplicate detection lifecycle."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        import_record.mark_as_duplicate()
        assert import_record.status == ImportStatus.DUPLICATE
        assert import_record.can_retry() is False

    def test_lifecycle_pending_to_skipped_to_retry(self):
        """Test skip and retry lifecycle."""
        bank_tx_id = uuid4()

        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )

        import_record.mark_as_skipped("Internal transfer")
        assert import_record.status == ImportStatus.SKIPPED

        import_record.retry()
        assert import_record.status == ImportStatus.PENDING

    def test_timestamps_are_set_correctly(self):
        """Test timestamp handling."""
        from datetime import timezone

        bank_tx_id = uuid4()

        before = datetime.now(tz=timezone.utc)
        import_record = TransactionImport(
            bank_transaction_id=bank_tx_id,
            user_id=TEST_USER_ID,
        )
        after = datetime.now(tz=timezone.utc)

        # created_at and updated_at should be set and be within the time window
        assert before <= import_record.created_at <= after
        assert before <= import_record.updated_at <= after

        # imported_at should be None for pending
        assert import_record.imported_at is None

        # After marking as imported, imported_at should be set
        import_record.mark_as_imported(uuid4())
        assert import_record.imported_at is not None
