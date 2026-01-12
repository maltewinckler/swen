"""
Unit tests for AccountRepositorySQLAlchemy.

These tests verify the persistence layer for accounting accounts.
"""

from uuid import UUID

import pytest
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.infrastructure.persistence.sqlalchemy.models import AccountModel
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    AccountRepositorySQLAlchemy,
)
from sqlalchemy import select

from tests.unit.infrastructure.persistence.conftest import TEST_USER_ID


class TestAccountRepositorySQLAlchemy:
    """Test suite for accounting account repository."""

    @pytest.mark.asyncio
    async def test_save_new_account(self, async_session, user_context):
        """Test saving a new accounting account."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account(
            name="Checking Account",
            account_type=AccountType.ASSET,
            account_number="1000",
            default_currency=Currency("EUR"),
            user_id=TEST_USER_ID,
        )

        # Act
        await repo.save(account)

        # Assert - verify it was saved
        retrieved = await repo.find_by_id(account.id)
        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.name == "Checking Account"
        assert retrieved.account_type == AccountType.ASSET
        assert retrieved.is_active is True

    @pytest.mark.asyncio
    async def test_save_updates_existing_account(self, async_session, user_context):
        """Test that saving an existing account updates it."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account("Test Account", AccountType.EXPENSE, "5000", TEST_USER_ID)
        await repo.save(account)

        # Act - modify and save again
        account.deactivate()
        await repo.save(account)

        # Assert
        retrieved = await repo.find_by_id(account.id)
        assert retrieved is not None
        assert retrieved.is_active is False

    @pytest.mark.asyncio
    async def test_find_by_name(self, async_session, user_context):
        """Test finding an account by name."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account("Office Supplies", AccountType.EXPENSE, "5001", TEST_USER_ID)
        await repo.save(account)

        # Act
        retrieved = await repo.find_by_name("Office Supplies")

        # Assert
        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.name == "Office Supplies"

    @pytest.mark.asyncio
    async def test_find_by_name_not_found(self, async_session, user_context):
        """Test finding a non-existent account returns None."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)

        # Act
        retrieved = await repo.find_by_name("NonExistent")

        # Assert
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_find_by_iban(self, async_session, user_context):
        """Find by iban should normalize and return matching account."""
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account(
            name="Bank Account",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            iban="DE89 3704 0044 0532 0130 00",
            default_currency=Currency("EUR"),
        )
        await repo.save(account)

        retrieved = await repo.find_by_iban("de89370400440532013000")
        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.iban == "DE89370400440532013000"

    @pytest.mark.asyncio
    async def test_save_duplicate_account_number_raises_error(self, async_session, user_context):
        """Duplicate account_number for same user should raise AccountAlreadyExistsError."""
        from swen.domain.accounting.exceptions import AccountAlreadyExistsError

        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        a1 = Account("A1", AccountType.ASSET, "1000", TEST_USER_ID)
        a2 = Account("A2", AccountType.ASSET, "1000", TEST_USER_ID)

        await repo.save(a1)
        with pytest.raises(AccountAlreadyExistsError, match="already exists"):
            await repo.save(a2)

    @pytest.mark.asyncio
    async def test_save_duplicate_iban_raises_error(self, async_session, user_context):
        """Duplicate iban for same user should raise AccountAlreadyExistsError."""
        from swen.domain.accounting.exceptions import AccountAlreadyExistsError

        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        a1 = Account(
            name="A1",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
        )
        a2 = Account(
            name="A2",
            account_type=AccountType.ASSET,
            account_number="BA-32013000-2",
            user_id=TEST_USER_ID,
            iban="DE89 3704 0044 0532 0130 00",
        )

        await repo.save(a1)
        with pytest.raises(AccountAlreadyExistsError, match="already mapped"):
            await repo.save(a2)

    @pytest.mark.asyncio
    async def test_find_all_active(self, async_session, user_context):
        """Test finding all active accounts."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)

        account1 = Account("Active 1", AccountType.ASSET, "1000", TEST_USER_ID)
        account2 = Account("Active 2", AccountType.EXPENSE, "5002", TEST_USER_ID)
        account3 = Account("Inactive", AccountType.INCOME, "4000", TEST_USER_ID)
        account3.deactivate()

        await repo.save(account1)
        await repo.save(account2)
        await repo.save(account3)

        # Act
        active_accounts = await repo.find_all_active()

        # Assert
        assert len(active_accounts) == 2
        names = {acc.name for acc in active_accounts}
        assert names == {"Active 1", "Active 2"}

    @pytest.mark.asyncio
    async def test_find_by_type(self, async_session, user_context):
        """Test finding accounts by type."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)

        asset1 = Account("Cash", AccountType.ASSET, "1001", TEST_USER_ID)
        asset2 = Account("Bank", AccountType.ASSET, "1002", TEST_USER_ID)
        expense = Account("Rent", AccountType.EXPENSE, "5003", TEST_USER_ID)

        await repo.save(asset1)
        await repo.save(asset2)
        await repo.save(expense)

        # Act
        assets = await repo.find_by_type(AccountType.ASSET.value)

        # Assert
        assert len(assets) == 2
        names = {acc.name for acc in assets}
        assert names == {"Cash", "Bank"}

    @pytest.mark.asyncio
    async def test_delete_account(self, async_session, user_context):
        """Test deleting an account."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account("To Delete", AccountType.ASSET, "1003", TEST_USER_ID)
        await repo.save(account)

        # Act
        await repo.delete(account.id)

        # Assert
        retrieved = await repo.find_by_id(account.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_account_with_parent(self, async_session, user_context):
        """Test saving and retrieving account with parent."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)

        parent = Account("Parent Account", AccountType.ASSET, "1004", TEST_USER_ID)
        await repo.save(parent)

        child = Account("Child Account", AccountType.ASSET, "1005", TEST_USER_ID)
        child.set_parent(parent)
        await repo.save(child)

        # Act
        retrieved = await repo.find_by_id(child.id)

        # Assert
        assert retrieved is not None
        assert retrieved.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_domain_to_model_mapping(self, async_session, user_context):
        """Test correct mapping between domain and database model."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, user_context)
        account = Account(
            name="Test Mapping",
            account_type=AccountType.ASSET,
            account_number="2000",
            default_currency=Currency("USD"),
            user_id=TEST_USER_ID,
        )
        await repo.save(account)

        # Act - query model directly
        stmt = select(AccountModel).where(AccountModel.id == account.id)
        result = await async_session.execute(stmt)
        model = result.scalar_one()

        # Assert
        assert model.id == account.id
        assert model.name == "Test Mapping"
        assert model.account_type == "asset"  # lowercase in the model
        assert model.default_currency == "USD"
        assert model.is_active is True
        assert model.iban is None
        # Compare without timezone for simplicity
        assert model.created_at.replace(tzinfo=None) == account.created_at.replace(
            tzinfo=None,
        )
