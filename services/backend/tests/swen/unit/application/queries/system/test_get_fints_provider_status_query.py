"""Unit tests for GetFintsProviderStatusQuery."""

from unittest.mock import AsyncMock

import pytest

from swen.application.system.queries.get_fints_provider_status_query import (
    GetFintsProviderStatusQuery,
)


def _make_repos(
    local_exists: bool = False,
    local_active: bool = False,
    api_exists: bool = False,
    api_active: bool = False,
) -> tuple[AsyncMock, AsyncMock]:
    fints_repo = AsyncMock()
    fints_repo.exists.return_value = local_exists
    fints_repo.is_active.return_value = local_active
    api_repo = AsyncMock()
    api_repo.exists.return_value = api_exists
    api_repo.is_active.return_value = api_active
    return fints_repo, api_repo


class TestGetFintsProviderStatusQuery:
    """Tests for GetFintsProviderStatusQuery."""

    @pytest.mark.asyncio
    async def test_no_provider_configured(self):
        fints_repo, api_repo = _make_repos()
        query = GetFintsProviderStatusQuery(
            fints_config_repo=fints_repo,
            geldstrom_api_config_repo=api_repo,
        )

        result = await query.execute()

        assert result.local_configured is False
        assert result.api_configured is False
        assert result.active_provider is None

    @pytest.mark.asyncio
    async def test_local_active(self):
        fints_repo, api_repo = _make_repos(local_exists=True, local_active=True)
        query = GetFintsProviderStatusQuery(
            fints_config_repo=fints_repo,
            geldstrom_api_config_repo=api_repo,
        )

        result = await query.execute()

        assert result.local_configured is True
        assert result.local_active is True
        assert result.active_provider == "local"

    @pytest.mark.asyncio
    async def test_api_active_takes_priority_over_local(self):
        fints_repo, api_repo = _make_repos(
            local_exists=True,
            local_active=True,
            api_exists=True,
            api_active=True,
        )
        query = GetFintsProviderStatusQuery(
            fints_config_repo=fints_repo,
            geldstrom_api_config_repo=api_repo,
        )

        result = await query.execute()

        assert result.active_provider == "api"
