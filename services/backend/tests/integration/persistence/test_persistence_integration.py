"""
Integration tests for persistence layer with banking data.

These tests verify the complete data flow:
1. Mock data from FinTS-like source
2. Save through repositories
3. Retrieve and verify data integrity
4. Test complex scenarios (transactions with accounts, etc.)

These are NOT full end-to-end tests (no real FinTS connection).
They test that the persistence layer correctly handles banking domain data.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swen.application.context import UserContext
from swen.domain.banking.value_objects import BankAccount, BankTransaction
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)

# Test user for integration tests
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"


def create_test_user_context() -> UserContext:
    """Create a UserContext for testing."""
    return UserContext(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


# ============================================================================
# Fixtures for Integration Tests
# ============================================================================


@pytest.fixture(scope="module")
def integration_engine():
    """
    Create an async engine for integration tests.

    Uses in-memory SQLite for fast tests, but you could configure
    this to use a real PostgreSQL test database for more realistic testing.
    """
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,  # Set to True for SQL debugging
        future=True,
    )


@pytest_asyncio.fixture(scope="function")
async def integration_session(integration_engine):
    """
    Create a fresh database session for each integration test.

    Unlike unit tests, integration tests may span multiple operations,
    so we create tables once and clean up after each test.
    """
    # Create all tables
    async with integration_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session for test
    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Clean up
    async with integration_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Helper Functions to Simulate FinTS Data
# ============================================================================


def create_fints_like_account(**overrides: object) -> BankAccount:
    """
    Create a bank account that looks like data from FinTS.

    FinTS returns accounts with all required fields populated.
    """
    defaults: dict[str, object] = {
        "iban": "DE89370400440532013000",
        "account_number": "532013000",
        "blz": "37040044",
        "account_holder": "Max Mustermann",
        "account_type": "Girokonto",
        "currency": "EUR",
        "bic": "COBADEFFXXX",
        "bank_name": "Commerzbank",
    }
    defaults.update(overrides)
    return BankAccount(**defaults)  # type: ignore[arg-type]


def create_fints_like_transaction(**overrides) -> BankTransaction:
    """
    Create a transaction that looks like data from FinTS.

    FinTS returns transactions with varying levels of detail.
    """
    defaults = {
        "booking_date": date(2025, 10, 30),
        "value_date": date(2025, 10, 30),
        "amount": Decimal("-50.00"),
        "currency": "EUR",
        "purpose": "REWE Sagt Danke",
        "applicant_name": "REWE",
        "applicant_iban": "DE12345678901234567890",
        "bank_reference": None,  # Often None from FinTS
    }
    defaults.update(overrides)
    return BankTransaction(**defaults)


# ============================================================================
# Integration Tests: Account Persistence
# ============================================================================


class TestAccountPersistenceIntegration:
    """Integration tests for account persistence."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_fints_account(self, integration_session):
        """Test saving and retrieving a FinTS-style account."""
        # Arrange - simulate receiving account from FinTS
        repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        fints_account = create_fints_like_account(
            iban="DE89370400440532013000",
            account_holder="Max Mustermann",
            bank_name="Commerzbank",
            balance=Decimal("1234.56"),
            balance_date=datetime(2025, 10, 30, 12, 0, 0, tzinfo=timezone.utc),
        )

        # Act - persist account
        await repo.save(fints_account)

        # Assert - retrieve and verify all fields
        retrieved = await repo.find_by_iban(fints_account.iban)

        assert retrieved is not None
        assert retrieved.iban == fints_account.iban
        assert retrieved.account_holder == fints_account.account_holder
        assert retrieved.bank_name == fints_account.bank_name
        assert retrieved.balance == fints_account.balance
        # Note: SQLite may lose timezone info, compare without timezone
        if retrieved.balance_date and fints_account.balance_date:
            assert retrieved.balance_date.replace(
                tzinfo=None,
            ) == fints_account.balance_date.replace(tzinfo=None)
        assert retrieved.currency == fints_account.currency

    @pytest.mark.skip(reason="update_balance() method not yet implemented")
    @pytest.mark.asyncio
    async def test_multiple_accounts_for_user(self, integration_session):
        """Test user with multiple bank accounts (common scenario)."""
        # Arrange
        repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        accounts = [
            create_fints_like_account(
                iban="DE89370400440532013000",
                account_holder="Max Mustermann",
                bank_name="Commerzbank",
                account_type="Girokonto",
            ),
            create_fints_like_account(
                iban="DE89370400440532013001",
                account_holder="Max Mustermann",
                bank_name="Commerzbank",
                account_type="Sparkonto",
            ),
            create_fints_like_account(
                iban="DE12500000001234567890",
                account_holder="Max Mustermann",
                bank_name="ING-DiBa",
                account_type="Girokonto",
            ),
        ]

        # Act - save all accounts
        for account in accounts:
            await repo.save(account)

        # Assert - all accounts retrievable
        retrieved = await repo.find_all()
        assert len(retrieved) == 3

        ibans = {acc.iban for acc in retrieved}
        expected_ibans = {acc.iban for acc in accounts}
        assert ibans == expected_ibans


# ============================================================================
# Integration Tests: Transaction Persistence
# ============================================================================


class TestTransactionPersistenceIntegration:
    """Integration tests for transaction persistence with accounts."""

    @pytest.mark.asyncio
    async def test_save_transactions_from_fints(self, integration_session):
        """Test saving transactions fetched from FinTS."""
        # Arrange - account exists
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # Simulate FinTS transaction fetch
        fints_transactions = [
            create_fints_like_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-30.50"),
                purpose="REWE Sagt Danke",
                applicant_name="REWE",
                bank_reference="REF001",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("2500.00"),
                purpose="Gehalt Oktober",
                applicant_name="Arbeitgeber GmbH",
                bank_reference="REF002",
            ),
        ]

        # Act - save transactions
        tx_ids = await tx_repo.save_batch(fints_transactions, account.iban)

        # Assert
        assert len(tx_ids) == 2

        # Verify all saved correctly
        all_transactions = await tx_repo.find_by_account(account.iban)
        assert len(all_transactions) == 2

        # Verify data integrity
        for original, retrieved in zip(
            fints_transactions,
            reversed(all_transactions),
            strict=False,
        ):
            assert retrieved.amount == original.amount
            assert retrieved.purpose == original.purpose
            assert retrieved.applicant_name == original.applicant_name

    @pytest.mark.asyncio
    async def test_incremental_transaction_sync(self, integration_session):
        """Test incremental sync (fetching only new transactions)."""
        # Arrange - account with existing transactions
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # Initial sync - October transactions
        october_transactions = [
            create_fints_like_transaction(
                booking_date=date(2025, 10, 1),
                bank_reference="OCT001",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 15),
                bank_reference="OCT002",
            ),
        ]
        await tx_repo.save_batch(october_transactions, account.iban)

        # Get latest transaction date
        latest_date = await tx_repo.get_latest_transaction_date(account.iban)
        assert latest_date == date(2025, 10, 15)

        # Act - incremental sync (new November transactions)
        november_transactions = [
            create_fints_like_transaction(
                booking_date=date(2025, 11, 1),
                bank_reference="NOV001",
            ),
        ]
        await tx_repo.save_batch(november_transactions, account.iban)

        # Assert - all transactions present
        all_transactions = await tx_repo.find_by_account(account.iban)
        assert len(all_transactions) == 3

        new_latest = await tx_repo.get_latest_transaction_date(account.iban)
        assert new_latest == date(2025, 11, 1)

    @pytest.mark.asyncio
    async def test_duplicate_transaction_prevention(self, integration_session):
        """Test that duplicate transactions are handled gracefully."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        transaction = create_fints_like_transaction(
            booking_date=date(2025, 10, 30),
            amount=Decimal("-50.00"),
            purpose="REWE Sagt Danke",
            bank_reference="UNIQUE-REF-001",
        )

        # Act - save once
        tx_id_1 = await tx_repo.save(transaction, account.iban)
        assert tx_id_1 is not None

        # Act - save again (should be idempotent)
        tx_id_2 = await tx_repo.save(transaction, account.iban)

        # Assert - same ID returned, only one transaction in database
        assert tx_id_1 == tx_id_2
        count = await tx_repo.count_by_account(account.iban)
        assert count == 1

    @pytest.mark.asyncio
    async def test_save_batch_handles_duplicates_gracefully(
        self,
        integration_session,
    ):
        """Test that save_batch gracefully skips duplicate transactions."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # First batch of transactions
        first_batch = [
            create_fints_like_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-30.00"),
                purpose="EDEKA",
                bank_reference="REF-001",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("-40.00"),
                purpose="REWE",
                bank_reference="REF-002",
            ),
        ]

        # Act - save first batch
        first_ids = await tx_repo.save_batch(first_batch, account.iban)
        assert len(first_ids) == 2

        # Second batch with overlap
        second_batch = [
            first_batch[0],  # Duplicate
            create_fints_like_transaction(
                booking_date=date(2025, 10, 30),
                amount=Decimal("-50.00"),
                purpose="DM",
                bank_reference="REF-003",
            ),  # New
        ]

        # Act - save second batch (should not raise error)
        second_ids = await tx_repo.save_batch(second_batch, account.iban)

        # Assert - returns both IDs
        assert len(second_ids) == 2

        # Verify total count is 3 (not 4)
        count = await tx_repo.count_by_account(account.iban)
        assert count == 3

    @pytest.mark.asyncio
    async def test_transactions_without_bank_reference(self, integration_session):
        """Test handling transactions without bank reference (common in FinTS)."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # Many FinTS transactions don't have bank_reference
        transactions = [
            create_fints_like_transaction(
                booking_date=date(2025, 10, 28),
                amount=Decimal("-10.00"),
                purpose="Coffee Shop",
                bank_reference=None,
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 29),
                amount=Decimal("-15.00"),
                purpose="Lunch",
                bank_reference=None,
            ),
        ]

        # Act - save transactions without bank_reference
        tx_ids = await tx_repo.save_batch(transactions, account.iban)

        # Assert - both saved (deterministic ID based on other fields)
        assert len(tx_ids) == 2

        retrieved = await tx_repo.find_by_account(account.iban)
        assert len(retrieved) == 2


# ============================================================================
# Integration Tests: Complex Scenarios
# ============================================================================


class TestComplexPersistenceScenarios:
    """Integration tests for complex real-world scenarios."""

    @pytest.mark.asyncio
    async def test_complete_sync_workflow(self, integration_session):
        """Test complete sync workflow: accounts + transactions."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        # Simulate FinTS sync: fetch accounts
        accounts = [
            create_fints_like_account(
                iban="DE89370400440532013000",
                account_holder="Max Mustermann",
                balance=Decimal("1500.00"),
            ),
            create_fints_like_account(
                iban="DE89370400440532013001",
                account_holder="Max Mustermann",
                balance=Decimal("5000.00"),
            ),
        ]

        # Act - save accounts
        for account in accounts:
            await acc_repo.save(account)

        # Simulate fetching transactions for each account
        for account in accounts:
            transactions = [
                create_fints_like_transaction(
                    booking_date=date(2025, 10, i),
                    bank_reference=f"REF-{account.iban[-4:]}-{i}",
                )
                for i in range(1, 11)  # 10 transactions per account
            ]
            await tx_repo.save_batch(transactions, account.iban)

        # Assert - verify complete data
        # Check accounts
        all_accounts = await acc_repo.find_all()
        assert len(all_accounts) == 2

        # Check transactions for each account
        for account in all_accounts:
            transactions = await tx_repo.find_by_account(account.iban)
            assert len(transactions) == 10

    @pytest.mark.asyncio
    async def test_account_deletion_cascades_to_transactions(
        self,
        integration_session,
    ):
        """Test that deleting account also deletes transactions."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # Add transactions
        transactions = [
            create_fints_like_transaction(
                bank_reference=f"REF{i}",
                end_to_end_reference=f"E2E-{i}",
                purpose=f"REWE Kauf {i}",
            )
            for i in range(5)
        ]
        tx_ids = await tx_repo.save_batch(transactions, account.iban)

        # Verify transactions exist
        assert len(tx_ids) == 5
        assert await tx_repo.count_by_account(account.iban) == 5

        # Act - delete account
        await acc_repo.delete(account.iban)

        # Assert - transactions should be gone (cascade delete)
        for tx_id in tx_ids:
            assert await tx_repo.find_by_id(tx_id) is None

    @pytest.mark.asyncio
    async def test_date_range_queries(self, integration_session):
        """Test querying transactions by date range (common for reports)."""
        # Arrange
        acc_repo = BankAccountRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        tx_repo = BankTransactionRepositorySQLAlchemy(
            integration_session,
            create_test_user_context(),
        )
        # User context is now provided via MockUserContext in repository constructor

        account = create_fints_like_account()
        await acc_repo.save(account)

        # Create transactions across multiple months
        transactions = [
            create_fints_like_transaction(
                booking_date=date(2025, 9, 15),
                bank_reference="SEP-001",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 5),
                bank_reference="OCT-001",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 15),
                bank_reference="OCT-002",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 10, 25),
                bank_reference="OCT-003",
            ),
            create_fints_like_transaction(
                booking_date=date(2025, 11, 5),
                bank_reference="NOV-001",
            ),
        ]
        await tx_repo.save_batch(transactions, account.iban)

        # Act - query October transactions only
        october_transactions = await tx_repo.find_by_account(
            account.iban,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
        )

        # Assert
        assert len(october_transactions) == 3
        for tx in october_transactions:
            assert date(2025, 10, 1) <= tx.booking_date <= date(2025, 10, 31)
