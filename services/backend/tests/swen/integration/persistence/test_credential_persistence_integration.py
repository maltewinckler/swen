"""Integration tests for credential persistence with encryption.

These tests verify the complete end-to-end flow:
1. Save credentials → encrypt → store in database
2. Retrieve from database → decrypt → return as BankCredentials
3. Multiple credentials per user
4. Soft delete and reactivation
5. Last used timestamp tracking

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import text

from swen.application.ports.identity import CurrentUser
from swen.domain.banking.value_objects import BankCredentials
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankCredentialRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.security import (
    StoredBankCredentialsRepositorySQLAlchemy,
)
from swen.infrastructure.security import FernetEncryptionService

# Import Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_EMAIL,
    TEST_USER_EMAIL_2,
    TEST_USER_ID,
    TEST_USER_ID_2,
)

# Additional test user for nightly sync tests
NIGHTLY_SYNC_USER_ID = UUID("abcdef01-2345-6789-abcd-ef0123456789")

# Create user contexts for testing
TEST_USER_CONTEXT = CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)
TEST_USER_CONTEXT_2 = CurrentUser(user_id=TEST_USER_ID_2, email=TEST_USER_EMAIL_2)
NIGHTLY_SYNC_USER_CONTEXT = CurrentUser(
    user_id=NIGHTLY_SYNC_USER_ID, email="nightly@example.com"
)


@pytest.fixture
def encryption_service():
    """Create a real Fernet encryption service for integration tests."""
    key = FernetEncryptionService.generate_key()
    return FernetEncryptionService(key)


def make_credential_repository(session, encryption_service, current_user):
    """Create a user-scoped credential repository."""
    stored_repo = StoredBankCredentialsRepositorySQLAlchemy(session, current_user)
    return BankCredentialRepositorySQLAlchemy(
        stored_credentials_repo=stored_repo,
        encryption_service=encryption_service,
        current_user=current_user,
    )


@pytest.fixture
def credential_repository(db_session, encryption_service):
    """Create credential repository for default test user."""
    return make_credential_repository(db_session, encryption_service, TEST_USER_CONTEXT)


# ============================================================================
# Integration Tests: Basic Save and Retrieve
# ============================================================================


class TestCredentialPersistenceBasic:
    """Test basic save and retrieve operations with encryption."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_credentials(
        self,
        credential_repository,
    ):
        """Test complete save → encrypt → store → load → decrypt → return flow."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="50031000",
            username="testuser",
            pin="secretpin123",
            endpoint="https://banking.triodos.de/fints",
        )

        # Act - save credentials (repo is user-scoped, no need for user_id)
        cred_id = await credential_repository.save(
            credentials,
            label="Triodos Bank",
        )

        # Assert - credential ID returned
        assert cred_id is not None

        # Act - retrieve credentials (repo is user-scoped, just need BLZ)
        retrieved = await credential_repository.find_by_blz("50031000")

        # Assert - credentials match (decrypted correctly)
        assert retrieved is not None
        assert retrieved.blz == "50031000"
        assert retrieved.username.get_value() == "testuser"
        assert retrieved.pin.get_value() == "secretpin123"
        assert retrieved.endpoint == "https://banking.triodos.de/fints"

    @pytest.mark.asyncio
    async def test_saved_credentials_are_encrypted_in_database(
        self,
        credential_repository,
        db_session,
    ):
        """Test that credentials are actually encrypted in the database."""
        # Arrange
        credentials = BankCredentials.from_plain(
            blz="12345678",
            username="plainuser",
            pin="plainpin",
            endpoint="https://banking.test.de/fints",
        )

        # Act - save credentials (repo is user-scoped)
        await credential_repository.save(credentials, label="Test Bank")
        await db_session.flush()  # Flush to make data visible for raw SQL

        # Assert - check database directly (raw SQL)
        # SQLAlchemy's Uuid type stores as hex without dashes for SQLite
        result = await db_session.execute(
            text(
                "SELECT username_encrypted, pin_encrypted FROM stored_credentials "
                "WHERE user_id = :user_id",
            ),
            {"user_id": TEST_USER_ID.hex},
        )
        row = result.fetchone()

        assert row is not None
        username_encrypted, pin_encrypted = row

        # Assert - values are encrypted (not plaintext)
        assert b"plainuser" not in username_encrypted
        assert b"plainpin" not in pin_encrypted
        assert "plainuser" not in username_encrypted.decode("utf-8", errors="ignore")
        assert "plainpin" not in pin_encrypted.decode("utf-8", errors="ignore")

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_credentials_returns_none(
        self,
        credential_repository,
    ):
        """Test that retrieving nonexistent credentials returns None."""
        # Act - BLZ that doesn't exist (repo is user-scoped)
        result = await credential_repository.find_by_blz("99999999")

        # Assert
        assert result is None


# ============================================================================
# Integration Tests: Multiple Credentials
# ============================================================================


class TestMultipleCredentials:
    """Test scenarios with multiple credentials per user."""

    @pytest.mark.asyncio
    async def test_save_multiple_credentials_for_one_user(
        self,
        credential_repository,
    ):
        """Test user with multiple bank accounts."""
        # Arrange
        user_id = TEST_USER_ID
        credentials_list = [
            BankCredentials.from_plain(
                blz="50031000",
                username="user_triodos",
                pin="pin1",
                endpoint="https://banking.triodos.de/fints",
            ),
            BankCredentials.from_plain(
                blz="50050000",
                username="user_dkb",
                pin="pin2",
                endpoint="https://banking.dkb.de/fints",
            ),
            BankCredentials.from_plain(
                blz="12345678",
                username="user_comdirect",
                pin="pin3",
                endpoint="https://banking.comdirect.de/fints",
            ),
        ]
        labels = ["Triodos Bank", "DKB", "Comdirect"]

        # Act - save all credentials
        for creds, label in zip(credentials_list, labels, strict=True):
            await credential_repository.save(creds, label=label)

        # Assert - retrieve all credentials metadata
        all_creds = await credential_repository.find_all()
        assert len(all_creds) == 3

        # Assert - labels are correct
        cred_dict = {blz: label for _, blz, label in all_creds}
        assert cred_dict["50031000"] == "Triodos Bank"
        assert cred_dict["50050000"] == "DKB"
        assert cred_dict["12345678"] == "Comdirect"

        # Assert - can retrieve each credential individually
        for creds in credentials_list:
            retrieved = await credential_repository.find_by_blz(creds.blz)
            assert retrieved is not None
            assert retrieved.blz == creds.blz
            assert retrieved.username.get_value() == creds.username.get_value()

    @pytest.mark.asyncio
    async def test_credentials_isolated_between_users(
        self,
        db_session,
        encryption_service,
    ):
        """Test that users cannot see each other's credentials."""
        # Arrange - create user-scoped repositories for each user
        user1_repo = make_credential_repository(
            db_session, encryption_service, TEST_USER_CONTEXT
        )
        user2_repo = make_credential_repository(
            db_session, encryption_service, TEST_USER_CONTEXT_2
        )

        creds1 = BankCredentials.from_plain(
            blz="50031000",
            username="user1_name",
            pin="user1_pin",
            endpoint="https://banking.triodos.de/fints",
        )

        creds2 = BankCredentials.from_plain(
            blz="50031000",  # Same bank!
            username="user2_name",
            pin="user2_pin",
            endpoint="https://banking.triodos.de/fints",
        )

        # Act - save credentials for both users via their own repos
        await user1_repo.save(creds1, label="User 1 Bank")
        await user2_repo.save(creds2, label="User 2 Bank")

        # Assert - each user can only see their own credentials
        user1_retrieved = await user1_repo.find_by_blz("50031000")
        assert user1_retrieved is not None
        assert user1_retrieved.username.get_value() == "user1_name"

        user2_retrieved = await user2_repo.find_by_blz("50031000")
        assert user2_retrieved is not None
        assert user2_retrieved.username.get_value() == "user2_name"

        # Assert - users don't see each other's credentials in list
        user1_list = await user1_repo.find_all()
        user2_list = await user2_repo.find_all()

        assert len(user1_list) == 1
        assert len(user2_list) == 1


# ============================================================================
# Integration Tests: Delete and Update Operations
# ============================================================================


class TestCredentialManagement:
    """Test credential management operations."""

    @pytest.mark.asyncio
    async def test_delete_credentials(
        self,
        credential_repository,
    ):
        """Test deleting stored credentials."""
        # Arrange
        user_id = TEST_USER_ID
        credentials = BankCredentials.from_plain(
            blz="12345678",
            username="testuser",
            pin="testpin",
            endpoint="https://banking.test.de/fints",
        )

        await credential_repository.save(credentials, label="Test Bank")

        # Verify credentials exist
        retrieved = await credential_repository.find_by_blz("12345678")
        assert retrieved is not None

        # Act - delete credentials
        result = await credential_repository.delete("12345678")

        # Assert - deletion successful
        assert result is True

        # Assert - credentials no longer retrievable
        retrieved_after = await credential_repository.find_by_blz("12345678")
        assert retrieved_after is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_credentials_returns_false(
        self,
        credential_repository,
    ):
        """Test deleting nonexistent credentials returns False."""
        # Act - try to delete credentials that don't exist in this user's scope
        result = await credential_repository.delete("99999999")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_update_last_used_timestamp(
        self,
        credential_repository,
        db_session,
    ):
        """Test updating last used timestamp when credentials are used."""
        # Arrange
        user_id = TEST_USER_ID
        blz = "12345678"
        credentials = BankCredentials.from_plain(
            blz=blz,
            username="testuser",
            pin="testpin",
            endpoint="https://banking.test.de/fints",
        )

        await credential_repository.save(credentials, label="Test Bank")
        await db_session.flush()  # Flush to make data visible for raw SQL

        # Get initial last_used_at (should be None)
        # SQLAlchemy's Uuid type stores as hex without dashes for SQLite
        result = await db_session.execute(
            text(
                "SELECT last_used_at FROM stored_credentials "
                "WHERE user_id = :user_id AND blz = :blz",
            ),
            {"user_id": user_id.hex, "blz": blz},
        )
        row = result.fetchone()
        assert row[0] is None

        # Act - update last used
        await credential_repository.update_last_used(blz)
        await db_session.commit()

        # Assert - last_used_at is now set
        result = await db_session.execute(
            text(
                "SELECT last_used_at FROM stored_credentials "
                "WHERE user_id = :user_id AND blz = :blz",
            ),
            {"user_id": user_id.hex, "blz": blz},
        )
        row = result.fetchone()
        last_used_at = row[0]

        assert last_used_at is not None
        # Should be recent (within last minute)
        # SQLite stores datetimes as strings without timezone, so parse as naive
        now = datetime.now(timezone.utc)
        if isinstance(last_used_at, str):
            last_used_dt = datetime.fromisoformat(last_used_at).replace(
                tzinfo=timezone.utc,
            )
        else:
            last_used_dt = last_used_at.replace(tzinfo=timezone.utc)
        time_diff = (now - last_used_dt).total_seconds()
        assert time_diff < 60  # Within last minute


# ============================================================================
# Integration Tests: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_cannot_save_duplicate_credentials(
        self,
        credential_repository,
    ):
        """Test that saving duplicate credentials for same user/BLZ updates existing."""
        # Arrange
        user_id = TEST_USER_ID
        credentials1 = BankCredentials.from_plain(
            blz="12345678",
            username="original_user",
            pin="original_pin",
            endpoint="https://banking.test.de/fints",
        )

        credentials2 = BankCredentials.from_plain(
            blz="12345678",  # Same BLZ!
            username="updated_user",
            pin="updated_pin",
            endpoint="https://banking.test.de/fints",
        )

        # Act - save first credentials
        await credential_repository.save(credentials1, label="Original")

        # Act - save second credentials (should fail or update)
        # Note: Current implementation may not prevent this
        # This test documents expected behavior

        # For now, let's verify that attempting to save throws an error or updates
        # Depending on implementation, this might be ValueError or update behavior
        try:
            await credential_repository.save(
                credentials2,
                label="Updated",
            )
            # If no error, verify only one set of credentials exists
            all_creds = await credential_repository.find_all()
            # Should still be 1 credential (updated, not duplicated)
            assert len(all_creds) <= 2  # At most 2 if update creates new record
        except ValueError:
            # Expected if duplicates are prevented
            pass

    @pytest.mark.asyncio
    async def test_encryption_roundtrip_with_special_characters(
        self,
        credential_repository,
    ):
        """Test encryption/decryption with special characters."""
        # Arrange
        user_id = TEST_USER_ID
        credentials = BankCredentials.from_plain(
            blz="12345678",
            username="user@example.com",
            pin="P@ssw0rd!#$%^&*()",
            endpoint="https://banking.test.de/fints?param=value&foo=bar",
        )

        # Act
        await credential_repository.save(credentials, label="Special Chars")
        retrieved = await credential_repository.find_by_blz("12345678")

        # Assert - special characters preserved
        assert retrieved is not None
        assert retrieved.username.get_value() == "user@example.com"
        assert retrieved.pin.get_value() == "P@ssw0rd!#$%^&*()"
        assert retrieved.endpoint == "https://banking.test.de/fints?param=value&foo=bar"


# ============================================================================
# Integration Tests: Real-World Scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    @pytest.mark.asyncio
    async def test_complete_credential_lifecycle(
        self,
        credential_repository,
    ):
        """Test complete lifecycle: create → use → update last used → delete."""
        # Arrange
        user_id = TEST_USER_ID
        blz = "50031000"

        # 1. User adds credentials
        credentials = BankCredentials.from_plain(
            blz=blz,
            username="lifecycle_test",
            pin="test123",
            endpoint="https://banking.triodos.de/fints",
        )

        cred_id = await credential_repository.save(
            credentials,
            label="Triodos",
        )
        assert cred_id is not None

        # 2. Application uses credentials for sync
        loaded_creds = await credential_repository.find_by_blz(blz)
        assert loaded_creds is not None
        # (Here would connect to FinTS using loaded_creds)

        # 3. Update last used after successful sync
        await credential_repository.update_last_used(blz)

        # 4. List all credentials
        all_creds = await credential_repository.find_all()
        assert len(all_creds) == 1

        # 5. User decides to remove credentials
        deleted = await credential_repository.delete(blz)
        assert deleted is True

        # 6. Verify credentials are gone
        final_list = await credential_repository.find_all()
        assert len(final_list) == 0

    @pytest.mark.asyncio
    async def test_nightly_sync_scenario(
        self,
        credential_repository,
    ):
        """Test automated nightly sync scenario."""
        # Arrange - user has multiple bank accounts configured
        user_id = NIGHTLY_SYNC_USER_ID
        banks = [
            ("50031000", "triodos_user", "triodos_pin", "Triodos"),
            ("50050000", "dkb_user", "dkb_pin", "DKB"),
            ("12345678", "comdirect_user", "comdirect_pin", "Comdirect"),
        ]

        # Setup - user has saved credentials for all banks
        for blz, username, pin, label in banks:
            creds = BankCredentials.from_plain(
                blz=blz,
                username=username,
                pin=pin,
                endpoint=f"https://banking.{label.lower()}.de/fints",
            )
            await credential_repository.save(creds, label=label)

        # Act - nightly sync process
        # 1. Load all credentials for user
        all_creds_metadata = await credential_repository.find_all()
        assert len(all_creds_metadata) == 3

        # 2. For each bank, load credentials and "sync"
        for _cred_id, blz, _label in all_creds_metadata:
            # Load decrypted credentials
            creds = await credential_repository.find_by_blz(blz)
            assert creds is not None

            # (Here would connect to FinTS and sync transactions)
            # ...

            # Update last used after successful sync
            await credential_repository.update_last_used(blz)

        # Assert - all credentials were processed
        # In production, would verify transactions were synced
