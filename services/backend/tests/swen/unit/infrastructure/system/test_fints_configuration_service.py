"""Unit tests for FinTSConfigurationService.

Tests verify:
- Product ID validation
- CSV validation (encoding, structure, content)
- Configuration status retrieval
"""

import csv
from io import StringIO

import pytest

from swen.infrastructure.banking.local_fints.services.configuration_service import (
    MAX_CSV_SIZE_BYTES,
    FinTSConfigurationService,
)


def _make_mock_repository():
    """Create a mock FinTSConfigRepository."""
    from unittest.mock import AsyncMock

    return AsyncMock()


def _make_service(repository=None) -> FinTSConfigurationService:
    """Create a FinTSConfigurationService with mock dependencies."""
    repo = repository or _make_mock_repository()
    return FinTSConfigurationService(config_repository=repo)


def _make_valid_csv_bytes(institute_count: int = 3) -> bytes:
    """Create valid CSV bytes in CP1252 encoding.

    Generates a CSV with the correct FinTS CSV structure:
    - Semicolon delimited
    - CP1252 encoded
    - Header row + data rows
    - BLZ at column 1, PIN/TAN URL at column 24
    """
    output = StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header row (25+ columns)
    header = [""] * 25
    header[0] = "Kennung"
    header[1] = "BLZ"
    header[2] = "BIC"
    header[3] = "Name"
    header[4] = "Ort"
    header[24] = "PIN/TAN-Zugang URL"
    writer.writerow(header)

    # Data rows
    for i in range(institute_count):
        row = [""] * 25
        row[1] = f"1004010{i}"  # BLZ - 8 digits
        row[2] = "BELADEBEXXX"
        row[3] = f"Test Bank {i}"
        row[4] = "Berlin"
        row[24] = f"https://banking.testbank{i}.de/fints"
        writer.writerow(row)

    return output.getvalue().encode("cp1252")


class TestValidateProductId:
    """Tests for Product ID validation."""

    def test_valid_product_id(self):
        service = _make_service()
        result = service.validate_product_id("12345678ABCDEF")
        assert result.is_valid is True
        assert result.error is None

    def test_empty_product_id(self):
        service = _make_service()
        result = service.validate_product_id("")
        assert result.is_valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_whitespace_only_product_id(self):
        service = _make_service()
        result = service.validate_product_id("   ")
        assert result.is_valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_product_id_too_long(self):
        service = _make_service()
        result = service.validate_product_id("A" * 101)
        assert result.is_valid is False
        assert result.error is not None
        assert "100" in result.error


class TestValidateCsv:
    """Tests for CSV validation."""

    def test_valid_csv(self):
        service = _make_service()
        csv_bytes = _make_valid_csv_bytes(institute_count=5)

        result = service.validate_csv(csv_bytes)

        assert result.is_valid is True
        assert result.institute_count == 5
        assert result.file_size_bytes > 0

    def test_empty_csv(self):
        service = _make_service()
        result = service.validate_csv(b"")
        assert result.is_valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_csv_too_large(self):
        service = _make_service()
        large_content = b"x" * (MAX_CSV_SIZE_BYTES + 1)
        result = service.validate_csv(large_content)
        assert result.is_valid is False
        assert result.error is not None
        assert "too large" in result.error.lower()

    def test_csv_header_only(self):
        """CSV with header but no data rows should fail."""
        service = _make_service()
        header = ";".join(["col"] * 25)
        csv_bytes = header.encode("cp1252")
        result = service.validate_csv(csv_bytes)
        assert result.is_valid is False
        assert result.error is not None
        assert "No valid institute" in result.error

    def test_csv_with_no_valid_institutes(self):
        """CSV with rows but no valid BLZ/URL combinations."""
        service = _make_service()
        output = StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([""] * 25)  # header
        # Row with missing URL
        row = [""] * 25
        row[1] = "10040100"
        writer.writerow(row)
        csv_bytes = output.getvalue().encode("cp1252")

        result = service.validate_csv(csv_bytes)
        assert result.is_valid is False
        assert result.error is not None
        assert "No valid institute" in result.error

    def test_csv_with_invalid_blz(self):
        """BLZ that is not 8 digits should be skipped."""
        service = _make_service()
        output = StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([""] * 25)  # header
        row = [""] * 25
        row[1] = "123"  # Too short
        row[24] = "https://banking.test.de"
        writer.writerow(row)
        csv_bytes = output.getvalue().encode("cp1252")

        result = service.validate_csv(csv_bytes)
        assert result.is_valid is False


class TestGetConfigurationStatus:
    """Tests for configuration status retrieval."""

    @pytest.mark.asyncio
    async def test_not_configured(self):
        repo = _make_mock_repository()
        repo.get_configuration.return_value = None
        service = _make_service(repository=repo)

        status = await service.get_configuration_status()

        assert status.is_configured is False

    @pytest.mark.asyncio
    async def test_configured(self):
        from datetime import datetime, timezone

        from swen.infrastructure.banking.local_fints.models.config import FinTSConfig

        repo = _make_mock_repository()
        repo.get_configuration.return_value = FinTSConfig(
            product_id="TEST",
            csv_content=b"data",
            csv_encoding="cp1252",
            csv_upload_timestamp=datetime.now(timezone.utc),
            csv_file_size_bytes=4,
            csv_institute_count=10,
            created_at=datetime.now(timezone.utc),
            created_by_id="admin-1",
            updated_at=datetime.now(timezone.utc),
            updated_by_id="admin-1",
        )
        service = _make_service(repository=repo)

        status = await service.get_configuration_status()

        assert status.is_configured is True
        assert status.has_product_id is True
        assert status.institute_count == 10


class TestUpdateConfiguration:
    """Tests for the unified update_configuration method."""

    @pytest.mark.asyncio
    async def test_neither_arg_raises(self):
        from uuid import UUID

        service = _make_service()
        admin_id = UUID("12345678-1234-5678-1234-567812345678")

        with pytest.raises(ValueError, match="At least one"):
            await service.update_configuration(admin_user_id=admin_id)

    @pytest.mark.asyncio
    async def test_first_time_product_id_only_raises(self):
        """First-time setup requires CSV — product_id alone must fail."""
        from uuid import UUID

        repo = _make_mock_repository()
        repo.exists.return_value = False
        service = _make_service(repository=repo)
        admin_id = UUID("12345678-1234-5678-1234-567812345678")

        with pytest.raises(ValueError, match="CSV is required"):
            await service.update_configuration(admin_user_id=admin_id, product_id="PID")

        repo.save_configuration.assert_not_called()

    @pytest.mark.asyncio
    async def test_first_time_both_fields_saves_config(self):
        """First-time setup with both fields calls save_configuration."""
        from uuid import UUID

        repo = _make_mock_repository()
        repo.exists.return_value = False
        service = _make_service(repository=repo)
        admin_id = UUID("12345678-1234-5678-1234-567812345678")
        csv_bytes = _make_valid_csv_bytes(institute_count=3)

        result = await service.update_configuration(
            admin_user_id=admin_id,
            product_id="VALID_PID",
            csv_content=csv_bytes,
        )

        repo.save_configuration.assert_called_once()
        assert result.institute_count == 3
        assert result.file_size_bytes is not None

    @pytest.mark.asyncio
    async def test_existing_product_id_only_patches_product_id(self):
        """When config exists, product_id-only update calls update_product_id only."""
        from uuid import UUID

        repo = _make_mock_repository()
        repo.exists.return_value = True
        service = _make_service(repository=repo)
        admin_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await service.update_configuration(
            admin_user_id=admin_id,
            product_id="VALID_PID",
        )

        repo.update_product_id.assert_called_once_with(
            product_id="VALID_PID",
            admin_user_id=admin_id,
        )
        repo.update_csv.assert_not_called()
        assert result.institute_count is None

    @pytest.mark.asyncio
    async def test_existing_csv_only_patches_csv(self):
        """When config exists, csv-only update calls update_csv only."""
        from uuid import UUID

        repo = _make_mock_repository()
        repo.exists.return_value = True
        service = _make_service(repository=repo)
        admin_id = UUID("12345678-1234-5678-1234-567812345678")
        csv_bytes = _make_valid_csv_bytes(institute_count=5)

        result = await service.update_configuration(
            admin_user_id=admin_id,
            csv_content=csv_bytes,
        )

        repo.update_csv.assert_called_once()
        repo.update_product_id.assert_not_called()
        assert result.institute_count == 5

    @pytest.mark.asyncio
    async def test_existing_both_fields_patches_both(self):
        """When config exists and both fields provided, both repo methods are called."""
        from uuid import UUID

        repo = _make_mock_repository()
        repo.exists.return_value = True
        service = _make_service(repository=repo)
        admin_id = UUID("12345678-1234-5678-1234-567812345678")
        csv_bytes = _make_valid_csv_bytes(institute_count=2)

        await service.update_configuration(
            admin_user_id=admin_id,
            product_id="PID",
            csv_content=csv_bytes,
        )

        repo.update_product_id.assert_called_once()
        repo.update_csv.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_product_id_raises(self):
        from uuid import UUID

        service = _make_service()
        admin_id = UUID("12345678-1234-5678-1234-567812345678")

        with pytest.raises(ValueError, match="Invalid Product ID"):
            await service.update_configuration(admin_user_id=admin_id, product_id="")

    @pytest.mark.asyncio
    async def test_invalid_csv_raises(self):
        from uuid import UUID

        service = _make_service()
        admin_id = UUID("12345678-1234-5678-1234-567812345678")

        with pytest.raises(ValueError, match="Invalid CSV"):
            await service.update_configuration(
                admin_user_id=admin_id,
                csv_content=b"",
            )
