"""Unit tests for GetGeldstromApiConfigQuery."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from swen.application.system.queries.geldstrom_api.get_geldstrom_api_config_query import (  # noqa: E501
    GetGeldstromApiConfigQuery,
)
from swen.infrastructure.banking.geldstrom_api.config import GeldstromApiConfig

TEST_ADMIN_ID = "12345678-1234-5678-1234-567812345678"


def _make_config(api_key: str = "abcdefghijklmnop") -> GeldstromApiConfig:
    now = datetime.now(timezone.utc)
    return GeldstromApiConfig(
        api_key=api_key,
        endpoint_url="https://api.geldstrom.example",
        is_active=True,
        created_at=now,
        created_by_id=TEST_ADMIN_ID,
        updated_at=now,
        updated_by_id=TEST_ADMIN_ID,
    )


class TestGetGeldstromApiConfigQuery:
    """Tests for GetGeldstromApiConfigQuery."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        repo = AsyncMock()
        repo.get_configuration.return_value = None
        query = GetGeldstromApiConfigQuery(config_repository=repo)

        result = await query.execute()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dto_with_masked_key_and_renamed_fields(self):
        repo = AsyncMock()
        config = _make_config(api_key="abcdefghijklmnop")
        repo.get_configuration.return_value = config
        query = GetGeldstromApiConfigQuery(config_repository=repo)

        result = await query.execute()

        assert result is not None
        assert result.api_key_masked == "abcd...mnop"
        assert result.endpoint_url == config.endpoint_url
        assert result.is_active is True
        assert result.last_updated == config.updated_at
        assert result.last_updated_by == config.updated_by_id

    def test_masks_short_api_key(self):
        assert GetGeldstromApiConfigQuery._mask_api_key("short") == "*****"

    def test_masks_long_api_key(self):
        assert (
            GetGeldstromApiConfigQuery._mask_api_key("abcdefghijklmnop")
            == "abcd...mnop"
        )
