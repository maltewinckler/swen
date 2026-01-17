"""
Unit tests for AccountMappingRepositorySQLAlchemy.

Tests the persistence of account mappings that link bank accounts to accounting accounts
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from swen.domain.integration.entities import AccountMapping
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    AccountMappingModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
)
from tests.shared.fixtures.database import TEST_USER_ID


# Helper function to create test mapping
def create_test_mapping(**overrides) -> AccountMapping:
    """Create a test account mapping with default values."""
    defaults = {
        "iban": "DE89370400440532013000",
        "accounting_account_id": uuid4(),
        "account_name": "DKB Checking Account",
        "is_active": True,
        "user_id": TEST_USER_ID,
    }
    defaults.update(overrides)
    return AccountMapping(**defaults)


@pytest.mark.asyncio
class TestAccountMappingRepositorySQLAlchemy:
    """Test suite for AccountMappingRepositorySQLAlchemy."""

    async def test_save_new_mapping(self, async_session, current_user):
        """Test saving a new account mapping."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()

        # Act
        await repo.save(mapping)
        await async_session.commit()

        # Assert - verify it was saved in database
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.id == mapping.id,
        )
        result = await async_session.execute(stmt)
        saved_model = result.scalar_one_or_none()

        assert saved_model is not None
        assert saved_model.id == mapping.id
        assert saved_model.iban == mapping.iban
        assert saved_model.accounting_account_id == mapping.accounting_account_id
        assert saved_model.account_name == mapping.account_name
        assert saved_model.is_active == mapping.is_active

    async def test_save_updates_existing_mapping(self, async_session, current_user):
        """Test that saving an existing mapping updates it."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act - update the mapping
        mapping.update_account_name("Updated Account Name")
        await repo.save(mapping)
        await async_session.commit()

        # Assert
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.id == mapping.id,
        )
        result = await async_session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        assert updated_model is not None
        assert updated_model.account_name == "Updated Account Name"

    async def test_find_by_id(self, async_session, current_user):
        """Test finding a mapping by ID."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act
        found_mapping = await repo.find_by_id(mapping.id)

        # Assert
        assert found_mapping is not None
        assert found_mapping.id == mapping.id
        assert found_mapping.iban == mapping.iban
        assert found_mapping.account_name == mapping.account_name

    async def test_find_by_id_returns_none_when_not_found(
        self, async_session, current_user
    ):
        """Test that find_by_id returns None for non-existent mapping."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        non_existent_id = uuid4()

        # Act
        found_mapping = await repo.find_by_id(non_existent_id)

        # Assert
        assert found_mapping is None

    async def test_find_by_iban(self, async_session, current_user):
        """Test finding a mapping by IBAN."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act
        found_mapping = await repo.find_by_iban(mapping.iban)

        # Assert
        assert found_mapping is not None
        assert found_mapping.id == mapping.id
        assert found_mapping.iban == mapping.iban

    async def test_find_by_iban_normalizes_iban(self, async_session, current_user):
        """Test that find_by_iban normalizes IBAN (case-insensitive)."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act - search with lowercase IBAN
        found_mapping = await repo.find_by_iban(mapping.iban.lower())

        # Assert
        assert found_mapping is not None
        assert found_mapping.iban == mapping.iban

    async def test_find_by_accounting_account_id(self, async_session, current_user):
        """Test finding all mappings for a specific accounting account."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        account_id = uuid4()

        mapping1 = create_test_mapping(
            iban="DE89370400440532013000",
            accounting_account_id=account_id,
        )
        mapping2 = create_test_mapping(
            iban="DE89370400440532013001",
            accounting_account_id=account_id,
        )
        mapping3 = create_test_mapping(
            iban="DE89370400440532013002",
            accounting_account_id=uuid4(),  # Different account
        )

        await repo.save(mapping1)
        await repo.save(mapping2)
        await repo.save(mapping3)
        await async_session.commit()

        # Act
        mappings = await repo.find_by_accounting_account_id(account_id)

        # Assert
        assert len(mappings) == 2
        assert all(m.accounting_account_id == account_id for m in mappings)

    async def test_find_all_active(self, async_session, current_user):
        """Test finding all active mappings."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)

        active_mapping = create_test_mapping(
            iban="DE89370400440532013000",
            is_active=True,
        )
        inactive_mapping = create_test_mapping(
            iban="DE89370400440532013001",
            is_active=False,
        )

        await repo.save(active_mapping)
        await repo.save(inactive_mapping)
        await async_session.commit()

        # Act
        active_mappings = await repo.find_all_active()

        # Assert
        assert len(active_mappings) == 1
        assert active_mappings[0].id == active_mapping.id
        assert active_mappings[0].is_active is True

    async def test_find_all(self, async_session, current_user):
        """Test finding all mappings (active and inactive)."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)

        mapping1 = create_test_mapping(
            iban="DE89370400440532013000",
            is_active=True,
        )
        mapping2 = create_test_mapping(
            iban="DE89370400440532013001",
            is_active=False,
        )

        await repo.save(mapping1)
        await repo.save(mapping2)
        await async_session.commit()

        # Act
        all_mappings = await repo.find_all()

        # Assert
        assert len(all_mappings) == 2

    async def test_delete_mapping(self, async_session, current_user):
        """Test deleting a mapping."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act
        deleted = await repo.delete(mapping.id)
        await async_session.commit()

        # Assert
        assert deleted is True

        # Verify it's gone from database
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.id == mapping.id,
        )
        result = await async_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_mapping_returns_false(
        self, async_session, current_user
    ):
        """Test that deleting a non-existent mapping returns False."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        non_existent_id = uuid4()

        # Act
        deleted = await repo.delete(non_existent_id)

        # Assert
        assert deleted is False

    async def test_exists_for_iban(self, async_session, current_user):
        """Test checking if a mapping exists for an IBAN."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping()
        await repo.save(mapping)
        await async_session.commit()

        # Act
        exists = await repo.exists_for_iban(mapping.iban)
        not_exists = await repo.exists_for_iban("DE89370400440532019999")

        # Assert
        assert exists is True
        assert not_exists is False

    async def test_domain_to_model_mapping_preserves_all_fields(
        self, async_session, current_user
    ):
        """Test that all domain fields are correctly mapped to model and back."""
        # Arrange
        repo = AccountMappingRepositorySQLAlchemy(async_session, current_user)
        mapping = create_test_mapping(
            account_name="Test Account",
            is_active=False,
        )

        # Act - save and retrieve
        await repo.save(mapping)
        await async_session.commit()
        retrieved_mapping = await repo.find_by_id(mapping.id)

        # Assert - all fields preserved
        assert retrieved_mapping is not None
        assert retrieved_mapping.id == mapping.id
        assert retrieved_mapping.iban == mapping.iban
        assert retrieved_mapping.accounting_account_id == mapping.accounting_account_id
        assert retrieved_mapping.account_name == mapping.account_name
        assert retrieved_mapping.is_active == mapping.is_active
        assert retrieved_mapping.created_at.replace(
            tzinfo=None,
        ) == mapping.created_at.replace(
            tzinfo=None,
        )
