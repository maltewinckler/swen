"""Unit tests for AccountMappingRepositorySQLAlchemy."""

from uuid import uuid4

import pytest

from swen.domain.integration.entities import AccountMapping
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
)
from tests.unit.infrastructure.persistence.conftest import TEST_USER_ID


class TestAccountMappingRepositorySQLAlchemy:
    """Test AccountMappingRepository SQLAlchemy implementation."""

    @pytest.fixture
    async def repository(self, async_session, current_user):
        """Create repository instance."""
        return AccountMappingRepositorySQLAlchemy(async_session, current_user)

    @pytest.fixture
    def sample_account_id_1(self):
        """Sample accounting account ID."""
        return uuid4()

    @pytest.fixture
    def sample_account_id_2(self):
        """Second sample accounting account ID."""
        return uuid4()

    @pytest.fixture
    def sample_mapping_1(self, sample_account_id_1):
        """Create a sample account mapping."""
        return AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=sample_account_id_1,
            account_name="DKB Checking Account",
            is_active=True,
            user_id=TEST_USER_ID,
        )

    @pytest.fixture
    def sample_mapping_2(self, sample_account_id_2):
        """Create a second sample account mapping."""
        return AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=sample_account_id_2,
            account_name="DKB Savings Account",
            is_active=True,
            user_id=TEST_USER_ID,
        )

    async def test_save_and_find_by_id(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test saving and retrieving a mapping by ID."""
        # Save mapping
        await repository.save(sample_mapping_1)

        # Find by ID
        found = await repository.find_by_id(sample_mapping_1.id)

        assert found is not None
        assert found.id == sample_mapping_1.id
        assert found.iban == sample_mapping_1.iban
        assert found.accounting_account_id == sample_mapping_1.accounting_account_id
        assert found.account_name == sample_mapping_1.account_name
        assert found.is_active == sample_mapping_1.is_active

    async def test_save_and_find_by_iban(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test saving and retrieving a mapping by IBAN."""
        # Save mapping
        await repository.save(sample_mapping_1)

        # Find by IBAN
        found = await repository.find_by_iban(sample_mapping_1.iban)

        assert found is not None
        assert found.id == sample_mapping_1.id
        assert found.iban == sample_mapping_1.iban

    async def test_save_multiple_mappings_different_ibans(
        self,
        repository,
        sample_mapping_1,
        sample_mapping_2,
    ):
        """
        Test saving multiple mappings with different IBANs.

        This reproduces the bug from the notebook where the second
        bank account mapping is not stored properly.
        """
        # Save first mapping
        await repository.save(sample_mapping_1)

        # Save second mapping
        await repository.save(sample_mapping_2)

        # Find all mappings
        all_mappings = await repository.find_all()

        # Should have 2 mappings
        assert len(all_mappings) == 2, f"Expected 2 mappings, got {len(all_mappings)}"

        # Verify both IBANs are present
        ibans = {m.iban for m in all_mappings}
        assert sample_mapping_1.iban in ibans
        assert sample_mapping_2.iban in ibans

        # Verify we can find each by IBAN
        found_1 = await repository.find_by_iban(sample_mapping_1.iban)
        assert found_1 is not None
        assert found_1.iban == sample_mapping_1.iban

        found_2 = await repository.find_by_iban(sample_mapping_2.iban)
        assert found_2 is not None
        assert found_2.iban == sample_mapping_2.iban

    async def test_save_multiple_mappings_same_account_id(
        self,
        repository,
        sample_account_id_1,
    ):
        """
        Test saving multiple mappings pointing to same accounting account.

        This should be allowed (one accounting account can represent multiple
        bank accounts, e.g., if user consolidates).
        """
        mapping_1 = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=sample_account_id_1,
            account_name="Account 1",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        mapping_2 = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=sample_account_id_1,  # Same account!
            account_name="Account 2",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        # Save both
        await repository.save(mapping_1)
        await repository.save(mapping_2)

        # Find by accounting account ID
        mappings = await repository.find_by_accounting_account_id(sample_account_id_1)

        # Should have 2 mappings for the same account
        assert len(mappings) == 2

    async def test_save_idempotent_same_iban(
        self,
        repository,
        sample_account_id_1,
    ):
        """
        Test that saving the same IBAN twice is idempotent.

        Since AccountMapping generates deterministic UUIDs based on
        IBAN + accounting_account_id, saving the same mapping twice
        should update, not create duplicate.
        """
        iban = "DE89370400440532013000"

        mapping_1 = AccountMapping(
            iban=iban,
            accounting_account_id=sample_account_id_1,
            account_name="First Name",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        mapping_2 = AccountMapping(
            iban=iban,
            accounting_account_id=sample_account_id_1,
            account_name="Updated Name",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        # Both mappings should have same ID (deterministic)
        assert mapping_1.id == mapping_2.id

        # Save first
        await repository.save(mapping_1)

        # Verify saved
        found = await repository.find_by_iban(iban)
        assert found is not None
        assert found.account_name == "First Name"

        # Save second (should update)
        await repository.save(mapping_2)

        # Verify updated
        found = await repository.find_by_iban(iban)
        assert found is not None
        assert found.account_name == "Updated Name"

        # Should only have 1 mapping
        all_mappings = await repository.find_all()
        assert len(all_mappings) == 1

    async def test_find_by_iban_normalizes_case(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test that IBAN lookup is case-insensitive."""
        await repository.save(sample_mapping_1)

        # Find with lowercase
        found = await repository.find_by_iban(sample_mapping_1.iban.lower())
        assert found is not None

        # Find with mixed case
        mixed_case_iban = (
            sample_mapping_1.iban.lower()[:5] + sample_mapping_1.iban.upper()[5:]
        )
        found = await repository.find_by_iban(mixed_case_iban)
        assert found is not None

    async def test_find_by_iban_strips_whitespace(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test that IBAN lookup strips whitespace."""
        await repository.save(sample_mapping_1)

        # Find with leading/trailing whitespace
        found = await repository.find_by_iban(f"  {sample_mapping_1.iban}  ")
        assert found is not None

    async def test_exists_for_iban(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test checking if mapping exists for IBAN."""
        # Should not exist initially
        assert not await repository.exists_for_iban(sample_mapping_1.iban)

        # Save mapping
        await repository.save(sample_mapping_1)

        # Should exist now
        assert await repository.exists_for_iban(sample_mapping_1.iban)

    async def test_find_all_active(
        self,
        repository,
        sample_account_id_1,
        sample_account_id_2,
    ):
        """Test finding only active mappings."""
        active_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=sample_account_id_1,
            account_name="Active Account",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        inactive_mapping = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=sample_account_id_2,
            account_name="Inactive Account",
            is_active=False,
            user_id=TEST_USER_ID,
        )

        # Save both
        await repository.save(active_mapping)
        await repository.save(inactive_mapping)

        # Find only active
        active_mappings = await repository.find_all_active()

        assert len(active_mappings) == 1
        assert active_mappings[0].iban == active_mapping.iban
        assert active_mappings[0].is_active is True

    async def test_find_all(
        self,
        repository,
        sample_account_id_1,
        sample_account_id_2,
    ):
        """Test finding all mappings regardless of status."""
        active_mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=sample_account_id_1,
            account_name="Active Account",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        inactive_mapping = AccountMapping(
            iban="DE89370400440532013001",
            accounting_account_id=sample_account_id_2,
            account_name="Inactive Account",
            is_active=False,
            user_id=TEST_USER_ID,
        )

        # Save both
        await repository.save(active_mapping)
        await repository.save(inactive_mapping)

        # Find all
        all_mappings = await repository.find_all()

        assert len(all_mappings) == 2

    async def test_delete(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test deleting a mapping."""
        # Save mapping
        await repository.save(sample_mapping_1)

        # Verify exists
        assert await repository.exists_for_iban(sample_mapping_1.iban)

        # Delete
        deleted = await repository.delete(sample_mapping_1.id)
        assert deleted is True

        # Verify deleted
        assert not await repository.exists_for_iban(sample_mapping_1.iban)

    async def test_delete_nonexistent(
        self,
        repository,
    ):
        """Test deleting a mapping that doesn't exist."""
        fake_id = uuid4()
        deleted = await repository.delete(fake_id)
        assert deleted is False

    async def test_update_existing_mapping(
        self,
        repository,
        sample_mapping_1,
    ):
        """Test updating an existing mapping."""
        # Save initial mapping
        await repository.save(sample_mapping_1)

        # Modify and save again
        sample_mapping_1.deactivate()
        await repository.save(sample_mapping_1)

        # Verify updated
        found = await repository.find_by_id(sample_mapping_1.id)
        assert found is not None
        assert found.is_active is False

    async def test_multiple_mappings_for_same_bank_scenario(
        self,
        repository,
        sample_account_id_1,
        sample_account_id_2,
    ):
        """
        Test the exact scenario from the notebook:
        User has 2 bank accounts from Triodos and imports both.

        This is the key test that should reproduce the bug.
        """
        # Simulate 2 bank accounts from Triodos
        triodos_account_1 = AccountMapping(
            iban="NL12TRIO0123456789",
            accounting_account_id=sample_account_id_1,
            account_name="Triodos - Betaalrekening",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        triodos_account_2 = AccountMapping(
            iban="NL34TRIO0987654321",
            accounting_account_id=sample_account_id_2,
            account_name="Triodos - Spaarrekening",
            is_active=True,
            user_id=TEST_USER_ID,
        )

        # Save first account
        await repository.save(triodos_account_1)

        # Verify first account was saved
        found_1 = await repository.find_by_iban(triodos_account_1.iban)
        assert found_1 is not None, "First Triodos account should be saved"

        # Save second account
        await repository.save(triodos_account_2)

        # Verify second account was saved
        found_2 = await repository.find_by_iban(triodos_account_2.iban)
        assert found_2 is not None, "Second Triodos account should be saved"

        # Verify both accounts exist
        all_mappings = await repository.find_all()
        expected_count = 2
        actual_count = len(all_mappings)
        assert actual_count == expected_count, (
            f"Expected {expected_count} Triodos accounts, got {actual_count}"
        )

        # Verify both can be found by IBAN
        assert await repository.exists_for_iban(triodos_account_1.iban)
        assert await repository.exists_for_iban(triodos_account_2.iban)
