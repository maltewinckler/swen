"""
Unit tests for BankTransactionRepositorySQLAlchemy.

Demonstrates advanced infrastructure testing:
1. Testing hash + sequence deduplication
2. Batch operations with identical transactions
3. Complex queries with filters
4. Foreign key relationships
5. Duplicate handling
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.banking.value_objects import BankAccount, BankTransaction
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)


def create_current_user(user_id: str = "test-user") -> MagicMock:
    """Create a mock CurrentUser for testing."""
    context = MagicMock()
    context.user_id = (
        UUID(user_id) if "-" in user_id and len(user_id) == 36 else user_id
    )
    return context


# Helper fixture to create a test account
@pytest.fixture
async def test_account(async_session):
    """Create a test bank account."""
    account = BankAccount(
        iban="DE89370400440532013000",
        account_number="532013000",
        blz="37040044",
        account_holder="Max Mustermann",
        account_type="Girokonto",
        currency="EUR",
    )
    current_user = create_current_user("00000000-0000-0000-0000-000000000001")
    repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
    await repo.save(account)
    return account


# Helper function to create test transaction
def create_test_transaction(**overrides) -> BankTransaction:
    """Create a test transaction with default values."""
    defaults = {
        "booking_date": date(2025, 10, 30),
        "value_date": date(2025, 10, 30),
        "amount": Decimal("-50.00"),
        "currency": "EUR",
        "purpose": "Test transaction",
        "bank_reference": "REF123",
    }
    defaults.update(overrides)
    return BankTransaction(**defaults)


class TestBankTransactionRepositorySQLAlchemy:
    """Test suite for bank transaction repository."""

    @pytest.mark.asyncio
    async def test_save_transaction(self, async_session, test_account):
        """Test saving a single transaction."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = create_test_transaction()

        # Act
        transaction_id = await repo.save(transaction, test_account.iban)

        # Assert
        assert isinstance(transaction_id, UUID)
        retrieved = await repo.find_by_id(transaction_id)
        assert retrieved is not None
        assert retrieved.amount == transaction.amount
        assert retrieved.purpose == transaction.purpose

    @pytest.mark.asyncio
    async def test_save_transaction_with_hash_and_sequence(
        self,
        async_session,
        test_account,
    ):
        """Test that transactions are saved with identity hash and sequence."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = create_test_transaction(
            booking_date=date(2025, 10, 30),
            amount=Decimal("-100.00"),
            purpose="Unique transaction",
            bank_reference="REF-UNIQUE-001",
        )

        # Act - save transaction using the new method that returns StoredBankTransaction
        results = await repo.save_batch_with_deduplication(
            [transaction],
            test_account.iban,
        )

        # Assert - should return StoredBankTransaction with hash and sequence
        assert len(results) == 1
        stored = results[0]
        assert isinstance(stored, StoredBankTransaction)
        assert stored.hash_sequence == 1
        assert stored.identity_hash is not None
        assert stored.is_new is True

        # Verify transaction was saved
        retrieved = await repo.find_by_id(stored.id)
        assert retrieved is not None
        assert retrieved.amount == transaction.amount
        assert retrieved.purpose == transaction.purpose

    @pytest.mark.asyncio
    async def test_save_transaction_prevents_duplicates(
        self,
        async_session,
        test_account,
    ):
        """Test that attempting to save the same transaction twice is idempotent."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = create_test_transaction(
            booking_date=date(2025, 10, 30),
            amount=Decimal("-100.00"),
            purpose="Duplicate test transaction",
            bank_reference="REF-DUPLICATE-001",
        )

        # Act - save transaction first time
        first_results = await repo.save_batch_with_deduplication(
            [transaction],
            test_account.iban,
        )

        # Act - save again (should be idempotent, not raise error)
        second_results = await repo.save_batch_with_deduplication(
            [transaction],
            test_account.iban,
        )

        # Assert - same ID returned, only one transaction in database
        assert first_results[0].id == second_results[0].id
        assert first_results[0].is_new is True
        assert second_results[0].is_new is False
        count = await repo.count_by_account(test_account.iban)
        assert count == 1

    @pytest.mark.asyncio
    async def test_save_batch(self, async_session, test_account):
        """Test saving multiple transactions in batch."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transactions = [
            create_test_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-30.00"),
                purpose="Transaction 1",
                bank_reference="REF001",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("-40.00"),
                purpose="Transaction 2",
                bank_reference="REF002",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 30),
                amount=Decimal("-50.00"),
                purpose="Transaction 3",
                bank_reference="REF003",
            ),
        ]

        # Act
        transaction_ids = await repo.save_batch(transactions, test_account.iban)

        # Assert
        assert len(transaction_ids) == 3
        assert all(isinstance(tid, UUID) for tid in transaction_ids)

        # Verify all were saved
        all_transactions = await repo.find_by_account(test_account.iban)
        assert len(all_transactions) == 3

    @pytest.mark.asyncio
    async def test_save_batch_with_duplicates(self, async_session, test_account):
        """Test that save_batch gracefully handles duplicate transactions."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        # First batch - 3 transactions
        first_batch = [
            create_test_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-30.00"),
                purpose="Transaction 1",
                bank_reference="REF001",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("-40.00"),
                purpose="Transaction 2",
                bank_reference="REF002",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 30),
                amount=Decimal("-50.00"),
                purpose="Transaction 3",
                bank_reference="REF003",
            ),
        ]

        # Act - save first batch
        first_results = await repo.save_batch_with_deduplication(
            first_batch,
            test_account.iban,
        )

        # Assert - all 3 saved as new
        assert len(first_results) == 3
        assert all(r.is_new for r in first_results)

        # Act - save second batch with 2 duplicates and 1 new
        second_batch = [
            first_batch[0],  # Duplicate
            first_batch[1],  # Duplicate
            create_test_transaction(
                booking_date=date(2025, 10, 31),
                amount=Decimal("-60.00"),
                purpose="Transaction 4",
                bank_reference="REF004",
            ),  # New
        ]

        second_results = await repo.save_batch_with_deduplication(
            second_batch,
            test_account.iban,
        )

        # Assert - returns all 3 results (including duplicates)
        assert len(second_results) == 3
        # First two should be duplicates (not new)
        assert second_results[0].is_new is False
        assert second_results[1].is_new is False
        assert second_results[0].id == first_results[0].id
        assert second_results[1].id == first_results[1].id
        # Third should be new
        assert second_results[2].is_new is True

        # Verify database has exactly 4 transactions (no duplicates)
        all_transactions = await repo.find_by_account(test_account.iban)
        assert len(all_transactions) == 4

    @pytest.mark.asyncio
    async def test_save_batch_all_duplicates(self, async_session, test_account):
        """Test that save_batch works when all transactions are duplicates."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        transactions = [
            create_test_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-30.00"),
                purpose="Transaction 1",
                bank_reference="REF001",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("-40.00"),
                purpose="Transaction 2",
                bank_reference="REF002",
            ),
        ]

        # Act - save first time
        first_results = await repo.save_batch_with_deduplication(
            transactions,
            test_account.iban,
        )
        assert len(first_results) == 2
        assert all(r.is_new for r in first_results)

        # Act - save again (all duplicates)
        second_results = await repo.save_batch_with_deduplication(
            transactions,
            test_account.iban,
        )

        # Assert - same IDs returned, but marked as not new
        assert [r.id for r in second_results] == [r.id for r in first_results]
        assert all(not r.is_new for r in second_results)

        # Verify still only 2 transactions in database
        all_transactions = await repo.find_by_account(test_account.iban)
        assert len(all_transactions) == 2

    @pytest.mark.asyncio
    async def test_save_batch_identical_transactions_get_sequence_numbers(
        self,
        async_session,
        test_account,
    ):
        """Test that identical transactions in same batch get different sequence numbers."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        # Two identical transactions (like two Hostelworld refunds on same day)
        identical_transaction = create_test_transaction(
            booking_date=date(2025, 11, 10),
            amount=Decimal("3.10"),
            purpose="20251110125940 WWW.HOSTELWORLD.COM IE",
            bank_reference="STARTUMS",  # Same reference!
            applicant_name="WWW.HOSTELWORLD.COM/DUBLIN",
        )

        # Same transaction twice in batch
        transactions = [identical_transaction, identical_transaction]

        # Act
        results = await repo.save_batch_with_deduplication(
            transactions,
            test_account.iban,
        )

        # Assert - both saved with different sequence numbers
        assert len(results) == 2
        assert results[0].hash_sequence == 1
        assert results[1].hash_sequence == 2
        assert results[0].identity_hash == results[1].identity_hash
        assert results[0].id != results[1].id  # Different UUIDs
        assert all(r.is_new for r in results)

        # Verify database has 2 transactions
        all_transactions = await repo.find_by_account(test_account.iban)
        assert len(all_transactions) == 2

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none(self, async_session):
        """Test finding non-existent transaction."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        fake_uuid = UUID("00000000-0000-0000-0000-000000000000")

        # Act
        result = await repo.find_by_id(fake_uuid)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_account(self, async_session, test_account):
        """Test finding all transactions for an account."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transactions = [
            create_test_transaction(
                booking_date=date(2025, 10, i),
                purpose=f"Transaction {i}",
                bank_reference=f"REF{i}",
            )
            for i in range(1, 6)
        ]

        for tx in transactions:
            await repo.save(tx, test_account.iban)

        # Act
        retrieved = await repo.find_by_account(test_account.iban)

        # Assert
        assert len(retrieved) == 5
        # Should be ordered by date descending (most recent first)
        assert retrieved[0].booking_date >= retrieved[-1].booking_date

    @pytest.mark.asyncio
    async def test_find_by_account_with_date_range(
        self,
        async_session,
        test_account,
    ):
        """Test finding transactions within a date range."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transactions = [
            create_test_transaction(
                booking_date=date(2025, 10, 1),
                purpose="October 1",
                bank_reference="REF1",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 15),
                purpose="October 15",
                bank_reference="REF15",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 31),
                purpose="October 31",
                bank_reference="REF31",
            ),
        ]

        for tx in transactions:
            await repo.save(tx, test_account.iban)

        # Act - query for mid-month only
        retrieved = await repo.find_by_account(
            test_account.iban,
            start_date=date(2025, 10, 10),
            end_date=date(2025, 10, 20),
        )

        # Assert
        assert len(retrieved) == 1
        assert retrieved[0].booking_date == date(2025, 10, 15)

    @pytest.mark.asyncio
    async def test_find_by_account_returns_empty_list(
        self,
        async_session,
        test_account,
    ):
        """Test finding transactions for account with no transactions."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        # Act
        result = await repo.find_by_account(test_account.iban)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_exists_by_bank_reference(self, async_session, test_account):
        """Test checking if transaction exists by bank reference."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = create_test_transaction(bank_reference="UNIQUE-REF-123")
        await repo.save(transaction, test_account.iban)

        # Act & Assert
        assert await repo.exists(test_account.iban, "UNIQUE-REF-123")
        assert not await repo.exists(test_account.iban, "NON-EXISTENT-REF")

    @pytest.mark.asyncio
    async def test_get_latest_transaction_date(self, async_session, test_account):
        """Test getting the most recent transaction date."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transactions = [
            create_test_transaction(
                booking_date=date(2025, 10, 1),
                bank_reference="REF1",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 15),
                bank_reference="REF15",
            ),
            create_test_transaction(
                booking_date=date(2025, 10, 31),
                bank_reference="REF31",
            ),
        ]

        for tx in transactions:
            await repo.save(tx, test_account.iban)

        # Act
        latest_date = await repo.get_latest_transaction_date(test_account.iban)

        # Assert
        assert latest_date == date(2025, 10, 31)

    @pytest.mark.asyncio
    async def test_get_latest_transaction_date_returns_none(
        self,
        async_session,
        test_account,
    ):
        """Test getting latest date when no transactions exist."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        # Act
        result = await repo.get_latest_transaction_date(test_account.iban)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_account(self, async_session, test_account):
        """Test counting transactions for an account."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))

        # Initially zero
        assert await repo.count_by_account(test_account.iban) == 0

        # Add some transactions (vary purpose and bank_reference to ensure uniqueness)
        transactions = [
            create_test_transaction(
                purpose=f"Test transaction {i}",
                bank_reference=f"REF{i}",
            )
            for i in range(5)
        ]
        await repo.save_batch(transactions, test_account.iban)

        # Act
        count = await repo.count_by_account(test_account.iban)

        # Assert
        assert count == 5

    @pytest.mark.asyncio
    async def test_cascade_delete(self, async_session, test_account):
        """Test that deleting account also deletes its transactions."""
        # Arrange
        tx_repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        acc_repo = BankAccountRepositorySQLAlchemy(async_session, current_user)

        # Add transactions
        transaction = create_test_transaction()
        tx_id = await tx_repo.save(transaction, test_account.iban)

        # Verify transaction exists
        assert await tx_repo.find_by_id(tx_id) is not None

        # Act - delete account
        await acc_repo.delete(test_account.iban)

        # Assert - transaction should be gone too (cascade delete)
        assert await tx_repo.find_by_id(tx_id) is None

    @pytest.mark.asyncio
    async def test_domain_to_model_mapping_preserves_all_fields(
        self,
        async_session,
        test_account,
    ):
        """Test that all transaction fields are correctly mapped."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = BankTransaction(
            booking_date=date(2025, 10, 30),
            value_date=date(2025, 10, 31),
            amount=Decimal("-123.45"),
            currency="EUR",
            purpose="Complete transaction with all fields",
            applicant_name="John Doe",
            applicant_iban="DE12345678901234567890",
            applicant_bic="ABCDEFGH",
            bank_reference="BANK-REF-001",
            customer_reference="CUST-REF-001",
            end_to_end_reference="E2E-REF-001",
            mandate_reference="MANDATE-001",
            creditor_id="CREDITOR-123",
            transaction_code="123",
            posting_text="Posting text",
        )

        # Act
        tx_id = await repo.save(transaction, test_account.iban)
        retrieved = await repo.find_by_id(tx_id)

        # Assert - all fields preserved
        assert retrieved is not None
        assert retrieved.booking_date == transaction.booking_date
        assert retrieved.value_date == transaction.value_date
        assert retrieved.amount == transaction.amount
        assert retrieved.currency == transaction.currency
        assert retrieved.purpose == transaction.purpose
        assert retrieved.applicant_name == transaction.applicant_name
        assert retrieved.applicant_iban == transaction.applicant_iban
        assert retrieved.applicant_bic == transaction.applicant_bic
        assert retrieved.bank_reference == transaction.bank_reference
        assert retrieved.customer_reference == transaction.customer_reference
        assert retrieved.end_to_end_reference == transaction.end_to_end_reference
        assert retrieved.mandate_reference == transaction.mandate_reference
        assert retrieved.creditor_id == transaction.creditor_id
        assert retrieved.transaction_code == transaction.transaction_code
        assert retrieved.posting_text == transaction.posting_text

    @pytest.mark.asyncio
    async def test_save_raises_error_for_nonexistent_account(self, async_session):
        """Test that saving to non-existent account raises error."""
        # Arrange
        repo = BankTransactionRepositorySQLAlchemy(async_session, create_current_user("00000000-0000-0000-0000-000000000001"))
        transaction = create_test_transaction()

        # Act & Assert
        with pytest.raises(ValueError, match=r"Account with IBAN .* not found"):
            await repo.save(transaction, "DE00000000000000000000")
