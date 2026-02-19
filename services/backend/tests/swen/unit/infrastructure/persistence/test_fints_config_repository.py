"""Unit tests for FinTSConfigRepositorySQLAlchemy.

Tests verify:
- Save and retrieve configuration with encryption
- Singleton pattern enforcement
- Product ID and CSV independent updates
- Audit trail tracking
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from cryptography.fernet import Fernet

from swen.infrastructure.banking.fints_config import FinTSConfig
from swen.infrastructure.persistence.sqlalchemy.models.banking.fints_config_model import (
    FinTSConfigModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    FinTSConfigRepositorySQLAlchemy,
)
from swen.infrastructure.security.encryption_service_fernet import (
    FernetEncryptionService,
)

# Use the test user IDs from conftest
TEST_ADMIN_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_ADMIN_ID_2 = UUID("00000000-0000-0000-0000-000000000001")


def _make_encryption_service() -> FernetEncryptionService:
    """Create a FernetEncryptionService with a test key."""
    key = Fernet.generate_key()
    return FernetEncryptionService(encryption_key=key)


def _make_test_config(
    product_id: str = "TEST_PRODUCT_123",
    institute_count: int = 42,
) -> FinTSConfig:
    """Create a test FinTSConfig DTO."""
    now = datetime.now(timezone.utc)
    return FinTSConfig(
        product_id=product_id,
        csv_content=b"header;row\ndata;row",
        csv_encoding="cp1252",
        csv_upload_timestamp=now,
        csv_file_size_bytes=20,
        csv_institute_count=institute_count,
        created_at=now,
        created_by_id=str(TEST_ADMIN_ID),
        updated_at=now,
        updated_by_id=str(TEST_ADMIN_ID),
    )


class TestFinTSConfigRepositorySQLAlchemy:
    """Test suite for FinTS configuration repository."""

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_empty(self, async_session):
        """Test exists returns False when no configuration exists."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        result = await repo.exists()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_configuration_returns_none_when_empty(self, async_session):
        """Test get returns None when no configuration exists."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        result = await repo.get_configuration()

        assert result is None

    @pytest.mark.asyncio
    async def test_save_configuration_creates_new(self, async_session):
        """Test saving a new configuration."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)
        config = _make_test_config()

        await repo.save_configuration(config, TEST_ADMIN_ID)

        # Verify it exists
        assert await repo.exists() is True

    @pytest.mark.asyncio
    async def test_save_and_retrieve_configuration(self, async_session):
        """Test saving and retrieving configuration preserves data."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)
        config = _make_test_config(product_id="MY_SECRET_PRODUCT_ID")

        await repo.save_configuration(config, TEST_ADMIN_ID)

        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.product_id == "MY_SECRET_PRODUCT_ID"
        assert retrieved.csv_content == config.csv_content
        assert retrieved.csv_encoding == "cp1252"
        assert retrieved.csv_institute_count == 42

    @pytest.mark.asyncio
    async def test_product_id_is_encrypted_in_database(self, async_session):
        """Test that the Product ID is encrypted at rest."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)
        config = _make_test_config(product_id="PLAIN_TEXT_SECRET")

        await repo.save_configuration(config, TEST_ADMIN_ID)
        await async_session.flush()

        # Read raw model from database
        model = await async_session.get(FinTSConfigModel, 1)
        assert model is not None
        # Raw bytes should NOT contain the plain text
        assert b"PLAIN_TEXT_SECRET" not in model.product_id_encrypted

    @pytest.mark.asyncio
    async def test_save_configuration_updates_existing(self, async_session):
        """Test that saving again updates the existing row."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        config_v1 = _make_test_config(product_id="VERSION_1")
        await repo.save_configuration(config_v1, TEST_ADMIN_ID)

        config_v2 = _make_test_config(product_id="VERSION_2")
        await repo.save_configuration(config_v2, TEST_ADMIN_ID)

        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.product_id == "VERSION_2"

    @pytest.mark.asyncio
    async def test_update_product_id_only(self, async_session):
        """Test updating only the Product ID."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        # Create initial config
        config = _make_test_config(product_id="ORIGINAL_ID")
        await repo.save_configuration(config, TEST_ADMIN_ID)

        # Update only Product ID
        await repo.update_product_id("NEW_PRODUCT_ID", TEST_ADMIN_ID)

        # Verify Product ID changed but CSV unchanged
        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.product_id == "NEW_PRODUCT_ID"
        assert retrieved.csv_content == config.csv_content

    @pytest.mark.asyncio
    async def test_update_product_id_fails_without_config(self, async_session):
        """Test that updating Product ID fails if no config exists."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        with pytest.raises(ValueError, match="configuration does not exist"):
            await repo.update_product_id("SOME_ID", TEST_ADMIN_ID)

    @pytest.mark.asyncio
    async def test_update_csv_only(self, async_session):
        """Test updating only the CSV data."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        # Create initial config
        config = _make_test_config(product_id="KEEP_THIS")
        await repo.save_configuration(config, TEST_ADMIN_ID)

        # Update only CSV
        new_csv = b"new;csv;content\nrow;data;here"
        await repo.update_csv(new_csv, "cp1252", 100, TEST_ADMIN_ID)

        # Verify CSV changed but Product ID unchanged
        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.product_id == "KEEP_THIS"
        assert retrieved.csv_content == new_csv
        assert retrieved.csv_institute_count == 100
        assert retrieved.csv_file_size_bytes == len(new_csv)

    @pytest.mark.asyncio
    async def test_update_csv_fails_without_config(self, async_session):
        """Test that updating CSV fails if no config exists."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        with pytest.raises(ValueError, match="configuration does not exist"):
            await repo.update_csv(b"data", "cp1252", 1, TEST_ADMIN_ID)

    @pytest.mark.asyncio
    async def test_audit_trail_on_save(self, async_session):
        """Test that created_by and updated_by are set correctly."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)
        config = _make_test_config()

        await repo.save_configuration(config, TEST_ADMIN_ID)

        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.created_by_id == str(TEST_ADMIN_ID)
        assert retrieved.updated_by_id == str(TEST_ADMIN_ID)

    @pytest.mark.asyncio
    async def test_audit_trail_on_update(self, async_session):
        """Test that updated_by changes on update."""
        encryption = _make_encryption_service()
        repo = FinTSConfigRepositorySQLAlchemy(async_session, encryption)

        config = _make_test_config()
        await repo.save_configuration(config, TEST_ADMIN_ID)

        # Update with different admin
        await repo.update_product_id("NEW_ID", TEST_ADMIN_ID_2)

        retrieved = await repo.get_configuration()
        assert retrieved is not None
        assert retrieved.created_by_id == str(TEST_ADMIN_ID)
        assert retrieved.updated_by_id == str(TEST_ADMIN_ID_2)
