"""Unit tests for ListAccountMappingsQuery."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.integration.queries import ListAccountMappingsQuery


class TestListAccountMappingsQuery:
    """Tests for the ListAccountMappingsQuery."""

    @pytest.fixture
    def mock_mapping_repo(self):
        """Create a mock mapping repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_account_repo(self):
        """Create a mock account repository."""
        return AsyncMock()

    @pytest.fixture
    def sample_mapping(self):
        """Create a sample account mapping."""
        mapping = MagicMock()
        mapping.id = uuid4()
        mapping.iban = "DE89370400440532013000"
        mapping.account_name = "Checking Account"
        mapping.accounting_account_id = uuid4()
        mapping.created_at = datetime(2024, 12, 5, 10, 0, 0, tzinfo=timezone.utc)
        return mapping

    @pytest.fixture
    def sample_account(self):
        """Create a sample account."""
        account = MagicMock()
        account.id = uuid4()
        account.name = "Checking"
        account.account_number = "1000"
        return account

    @pytest.mark.asyncio
    async def test_execute_returns_mappings_list(
        self,
        mock_mapping_repo,
        mock_account_repo,
        sample_mapping,
        sample_account,
    ):
        """Test that execute returns a list of mappings with account info."""
        mock_mapping_repo.find_all.return_value = [sample_mapping]
        mock_account_repo.find_by_id.return_value = sample_account

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.execute()

        assert result.count == 1
        assert len(result.mappings) == 1
        assert result.mappings[0].iban == "DE89370400440532013000"
        assert result.mappings[0].accounting_account_name == "Checking"
        assert result.mappings[0].accounting_account_number == "1000"
        mock_mapping_repo.find_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list(
        self,
        mock_mapping_repo,
        mock_account_repo,
    ):
        """Test that execute returns empty list when no mappings exist."""
        mock_mapping_repo.find_all.return_value = []

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.execute()

        assert result.count == 0
        assert result.mappings == []

    @pytest.mark.asyncio
    async def test_execute_handles_null_account(
        self,
        mock_mapping_repo,
        mock_account_repo,
        sample_mapping,
    ):
        """Test that execute handles missing accounting account gracefully."""
        mock_mapping_repo.find_all.return_value = [sample_mapping]
        mock_account_repo.find_by_id.return_value = None

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.execute()

        assert result.count == 1
        assert result.mappings[0].accounting_account_name is None
        assert result.mappings[0].accounting_account_number is None

    @pytest.mark.asyncio
    async def test_get_by_iban_returns_mapping_with_account(
        self,
        mock_mapping_repo,
        mock_account_repo,
        sample_mapping,
        sample_account,
    ):
        """Test getting mapping by IBAN with resolved account."""
        mock_mapping_repo.find_by_iban.return_value = sample_mapping
        mock_account_repo.find_by_id.return_value = sample_account

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.get_by_iban("DE89370400440532013000")

        assert result is not None
        assert result.iban == "DE89370400440532013000"
        assert result.accounting_account_name == "Checking"
        assert result.accounting_account_number == "1000"

    @pytest.mark.asyncio
    async def test_get_by_iban_returns_none_when_mapping_not_found(
        self,
        mock_mapping_repo,
        mock_account_repo,
    ):
        """Test get_by_iban returns None when mapping not found."""
        mock_mapping_repo.find_by_iban.return_value = None

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.get_by_iban("INVALID_IBAN")

        assert result is None
        mock_account_repo.find_by_id.assert_not_called()


class TestListAccountMappingsQueryDependencyInjection:
    """Tests to verify proper dependency injection."""

    def test_query_requires_mapping_repository(self):
        """Test that query requires a mapping repository."""
        mock_repo = AsyncMock()
        mock_account = AsyncMock()
        query = ListAccountMappingsQuery(mock_repo, mock_account)
        assert query._mapping_repo is mock_repo

    def test_query_requires_account_repository(self):
        """Test that query requires account repository."""
        mock_mapping_repo = AsyncMock()
        mock_account_repo = AsyncMock()

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)

        assert query._mapping_repo is mock_mapping_repo
        assert query._account_repo is mock_account_repo
