"""Unit tests for FinTS configuration commands and queries.

Tests verify:
- Command execution with validation
- Query result masking
- Configuration status checks
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from swen.application.commands.system import UpdateLocalFinTSConfigCommand
from swen.application.queries.system import (
    GetFinTSConfigurationQuery,
    GetFinTSConfigurationStatusQuery,
)
from swen.infrastructure.banking.local_fints.models.config import FinTSConfig
from swen.infrastructure.banking.local_fints.services.configuration_service import (
    FinTSConfigurationService,
)

TEST_ADMIN_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_mock_repo() -> AsyncMock:
    return AsyncMock()


def _make_config(
    product_id: str = "ABCDEFGHIJKLMNOP",
    institute_count: int = 100,
) -> FinTSConfig:
    now = datetime.now(timezone.utc)
    return FinTSConfig(
        product_id=product_id,
        csv_content=b"csv;data",
        csv_encoding="cp1252",
        csv_upload_timestamp=now,
        csv_file_size_bytes=8,
        csv_institute_count=institute_count,
        created_at=now,
        created_by_id=str(TEST_ADMIN_ID),
        updated_at=now,
        updated_by_id=str(TEST_ADMIN_ID),
    )


class TestGetFinTSConfigurationQuery:
    """Tests for GetFinTSConfigurationQuery."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        repo = _make_mock_repo()
        repo.get_configuration.return_value = None
        query = GetFinTSConfigurationQuery(config_repository=repo)

        result = await query.execute()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dto_with_masked_product_id(self):
        repo = _make_mock_repo()
        repo.get_configuration.return_value = _make_config(
            product_id="ABCDEFGHIJKLMNOP"
        )
        query = GetFinTSConfigurationQuery(config_repository=repo)

        result = await query.execute()

        assert result is not None
        assert result.product_id_masked == "ABCD...MNOP"
        assert result.csv_institute_count == 100

    @pytest.mark.asyncio
    async def test_masks_short_product_id(self):
        repo = _make_mock_repo()
        repo.get_configuration.return_value = _make_config(product_id="SHORT")
        query = GetFinTSConfigurationQuery(config_repository=repo)

        result = await query.execute()

        assert result is not None
        assert result.product_id_masked == "*****"

    def test_mask_product_id_static_method(self):
        assert (
            GetFinTSConfigurationQuery._mask_product_id("ABCDEFGHIJ") == "ABCD...GHIJ"
        )
        assert GetFinTSConfigurationQuery._mask_product_id("12345678") == "********"
        assert GetFinTSConfigurationQuery._mask_product_id("AB") == "**"


class TestGetFinTSConfigurationStatusQuery:
    """Tests for GetFinTSConfigurationStatusQuery."""

    @pytest.mark.asyncio
    async def test_not_configured(self):
        repo = _make_mock_repo()
        repo.exists.return_value = False
        query = GetFinTSConfigurationStatusQuery(config_repository=repo)

        result = await query.execute()

        assert result.is_configured is False
        assert "not configured" in result.message

    @pytest.mark.asyncio
    async def test_configured(self):
        repo = _make_mock_repo()
        repo.exists.return_value = True
        query = GetFinTSConfigurationStatusQuery(config_repository=repo)

        result = await query.execute()

        assert result.is_configured is True
        assert "configured" in result.message


class TestUpdateLocalFinTSConfigCommand:
    """Tests for UpdateLocalFinTSConfigCommand."""

    def _make_command(self) -> UpdateLocalFinTSConfigCommand:
        repo = _make_mock_repo()
        repo.exists.return_value = True
        service = FinTSConfigurationService(config_repository=repo)
        return UpdateLocalFinTSConfigCommand(
            config_service=service,
            admin_user_id=TEST_ADMIN_ID,
        )

    @pytest.mark.asyncio
    async def test_execute_raises_when_no_args(self):
        command = self._make_command()

        with pytest.raises(ValueError, match="At least one"):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_product_id_only_does_not_populate_tables(self):
        repo = _make_mock_repo()
        repo.exists.return_value = True
        service = FinTSConfigurationService(config_repository=repo)
        command = UpdateLocalFinTSConfigCommand(
            config_service=service,
            admin_user_id=TEST_ADMIN_ID,
        )

        with patch.object(
            service, "populate_bank_tables", new_callable=AsyncMock
        ) as mock_populate:
            await command.execute(product_id="VALID_PRODUCT_ID")

        mock_populate.assert_not_called()
        repo.update_product_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_csv_only_calls_populate_bank_tables(self):
        repo = _make_mock_repo()
        repo.exists.return_value = True
        service = FinTSConfigurationService(config_repository=repo)
        command = UpdateLocalFinTSConfigCommand(
            config_service=service,
            admin_user_id=TEST_ADMIN_ID,
        )

        with (
            patch.object(
                service, "populate_bank_tables", new_callable=AsyncMock
            ) as mock_populate,
            patch.object(service, "validate_csv") as mock_validate,
        ):
            mock_validate.return_value = MagicMock(
                is_valid=True, institute_count=5, file_size_bytes=100
            )
            await command.execute(csv_content=b"some csv bytes")

        mock_populate.assert_called_once_with(b"some csv bytes")

    @pytest.mark.asyncio
    async def test_execute_both_args_calls_populate_bank_tables(self):
        repo = _make_mock_repo()
        repo.exists.return_value = True
        service = FinTSConfigurationService(config_repository=repo)
        command = UpdateLocalFinTSConfigCommand(
            config_service=service,
            admin_user_id=TEST_ADMIN_ID,
        )

        with (
            patch.object(
                service, "populate_bank_tables", new_callable=AsyncMock
            ) as mock_populate,
            patch.object(service, "validate_csv") as mock_validate,
        ):
            mock_validate.return_value = MagicMock(
                is_valid=True, institute_count=5, file_size_bytes=100
            )
            await command.execute(product_id="PID", csv_content=b"some csv bytes")

        mock_populate.assert_called_once_with(b"some csv bytes")
        repo.update_product_id.assert_called_once()
