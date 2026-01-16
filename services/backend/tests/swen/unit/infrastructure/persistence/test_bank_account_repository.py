"""
Unit tests for BankAccountRepositorySQLAlchemy.

These tests demonstrate key infrastructure testing patterns:
1. Using in-memory database for fast, isolated tests
2. Testing CRUD operations
3. Verifying domain-to-model mapping
4. Testing user-scoped behavior
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy import select

from swen.domain.banking.value_objects import BankAccount
from swen.infrastructure.persistence.sqlalchemy.models.banking import (
    BankAccountModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
)


# Helper function to create test account
def create_test_account(**overrides) -> BankAccount:
    """Create a test bank account with default values."""
    defaults = {
        "iban": "DE89370400440532013000",
        "account_number": "532013000",
        "blz": "37040044",
        "account_holder": "Max Mustermann",
        "account_type": "Girokonto",
        "currency": "EUR",
    }
    defaults.update(overrides)
    return BankAccount(**defaults)  # type: ignore[arg-type]


def create_current_user(user_id: str = "test-user-123") -> MagicMock:
    """Create a mock CurrentUser for testing."""
    context = MagicMock()
    context.user_id = UUID(user_id) if "-" in user_id else user_id
    return context


class TestBankAccountRepositorySQLAlchemy:
    """Test suite for bank account repository."""

    @pytest.mark.asyncio
    async def test_save_new_account(self, async_session):
        """Test saving a new bank account."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        account = BankAccount(
            iban="DE89370400440532013000",
            account_number="532013000",
            blz="37040044",
            bic="COBADEFFXXX",
            account_holder="Max Mustermann",
            bank_name="Commerzbank",
            account_type="Girokonto",
            currency="EUR",
        )

        # Act
        await repo.save(account)

        # Assert - verify it was saved by retrieving it
        retrieved = await repo.find_by_iban(account.iban)
        assert retrieved is not None
        assert retrieved.iban == account.iban
        assert retrieved.account_holder == account.account_holder
        assert retrieved.bank_name == account.bank_name
        assert retrieved.currency == account.currency

    @pytest.mark.asyncio
    async def test_save_updates_existing_account(self, async_session):
        """Test that saving an existing account updates it."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        iban = "DE89370400440532013000"

        # Create initial account
        account_v1 = create_test_account(
            iban=iban,
            bank_name="Bank A",
        )
        await repo.save(account_v1)

        # Act - save updated version
        account_v2 = create_test_account(
            iban=iban,
            bank_name="Bank B - Updated",  # Changed
        )
        await repo.save(account_v2)

        # Assert - should be updated, not duplicated
        retrieved = await repo.find_by_iban(iban)
        assert retrieved is not None
        assert retrieved.bank_name == "Bank B - Updated"

        # Verify only one account exists
        all_accounts = await repo.find_all()
        assert len(all_accounts) == 1

    @pytest.mark.asyncio
    async def test_save_same_account_is_idempotent(self, async_session):
        """Test that saving the exact same account multiple times is idempotent."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        iban = "DE89370400440532013000"

        account = create_test_account(
            iban=iban,
            bank_name="Commerzbank",
            account_holder="Max Mustermann",
        )

        # Act - save the same account three times
        await repo.save(account)
        await repo.save(account)
        await repo.save(account)

        # Assert - should have exactly one account with same data
        all_accounts = await repo.find_all()
        assert len(all_accounts) == 1

        retrieved = await repo.find_by_iban(iban)
        assert retrieved is not None
        assert retrieved.bank_name == "Commerzbank"
        assert retrieved.account_holder == "Max Mustermann"

    @pytest.mark.asyncio
    async def test_find_by_iban_returns_none_when_not_found(self, async_session):
        """Test finding a non-existent account returns None."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)

        # Act
        result = await repo.find_by_iban("DE00000000000000000000")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all(self, async_session):
        """Test finding all accounts for the current user."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)

        accounts = [
            create_test_account(iban="DE89370400440532013000"),
            create_test_account(iban="DE89370400440532013001"),
            create_test_account(iban="DE89370400440532013002"),
        ]

        for account in accounts:
            await repo.save(account)

        # Act
        retrieved = await repo.find_all()

        # Assert
        assert len(retrieved) == 3
        retrieved_ibans = {acc.iban for acc in retrieved}
        assert retrieved_ibans == {acc.iban for acc in accounts}

    @pytest.mark.asyncio
    async def test_find_all_returns_empty_list(self, async_session):
        """Test finding accounts for user with no accounts."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)

        # Act
        result = await repo.find_all()

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_account(self, async_session):
        """Test deleting an account."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        iban = "DE89370400440532013000"

        account = create_test_account(iban=iban)
        await repo.save(account)

        # Verify it exists
        assert await repo.find_by_iban(iban) is not None

        # Act
        await repo.delete(iban)

        # Assert
        assert await repo.find_by_iban(iban) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_account_is_noop(self, async_session):
        """Test deleting a non-existent account doesn't error."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)

        # Act & Assert - should not raise
        await repo.delete("DE00000000000000000000")

    @pytest.mark.asyncio
    async def test_user_isolation(self, async_session):
        """Test that accounts are isolated by user_id (user-scoped)."""
        # Arrange
        iban = "DE89370400440532013000"
        account = create_test_account(iban=iban)

        # Save for user A
        current_user_a = create_current_user("00000000-0000-0000-0000-000000000001")
        repo_a = BankAccountRepositorySQLAlchemy(async_session, current_user_a)
        await repo_a.save(account)

        # Act & Assert - user B shouldn't see it
        current_user_b = create_current_user("00000000-0000-0000-0000-000000000002")
        repo_b = BankAccountRepositorySQLAlchemy(async_session, current_user_b)
        result_user_b = await repo_b.find_by_iban(iban)
        assert result_user_b is None

        # User A should see it
        result_user_a = await repo_a.find_by_iban(iban)
        assert result_user_a is not None

    @pytest.mark.asyncio
    async def test_update_last_sync(self, async_session):
        """Test updating last sync timestamp."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        iban = "DE89370400440532013000"

        account = create_test_account(iban=iban)
        await repo.save(account)

        # Act
        sync_time = datetime(2025, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        await repo.update_last_sync(iban, sync_time)

        # Assert - check the database model directly (last_sync_at not exposed in domain)
        stmt = select(BankAccountModel).where(
            BankAccountModel.iban == iban,
            BankAccountModel.user_id == current_user.user_id,
        )
        result = await async_session.execute(stmt)
        model = result.scalar_one()
        assert model.last_sync_at is not None

    @pytest.mark.asyncio
    async def test_timestamps_are_set(self, async_session):
        """Test that created_at and updated_at timestamps are set."""
        # Arrange
        current_user = create_current_user("00000000-0000-0000-0000-000000000001")
        repo = BankAccountRepositorySQLAlchemy(async_session, current_user)
        iban = "DE89370400440532013000"

        account = create_test_account(iban=iban)

        # Act
        await repo.save(account)

        # Assert - check the database model directly
        stmt = select(BankAccountModel).where(
            BankAccountModel.iban == iban,
            BankAccountModel.user_id == current_user.user_id,
        )
        result = await async_session.execute(stmt)
        model = result.scalar_one()

        assert model.created_at is not None
        assert model.updated_at is not None
        # Both should be close to now (within 2 seconds)
        # Note: SQLite stores as naive datetime, so compare without timezone
        now_utc = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        created_at_naive = (
            model.created_at.replace(tzinfo=None)
            if model.created_at.tzinfo
            else model.created_at
        )
        assert (now_utc - created_at_naive).total_seconds() < 2
