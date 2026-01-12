"""Unit tests for ListAccountMappingsQuery."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from swen.application.queries import ListAccountMappingsQuery


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
        return mapping

    @pytest.mark.asyncio
    async def test_execute_returns_mappings_list(
        self,
        mock_mapping_repo,
        sample_mapping,
    ):
        """Test that execute returns a list of mappings."""
        mock_mapping_repo.find_all.return_value = [sample_mapping]

        query = ListAccountMappingsQuery(mock_mapping_repo)
        result = await query.execute()

        assert result.total_count == 1
        assert len(result.mappings) == 1
        assert result.mappings[0] == sample_mapping
        mock_mapping_repo.find_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list(self, mock_mapping_repo):
        """Test that execute returns empty list when no mappings exist."""
        mock_mapping_repo.find_all.return_value = []

        query = ListAccountMappingsQuery(mock_mapping_repo)
        result = await query.execute()

        assert result.total_count == 0
        assert result.mappings == []

    @pytest.mark.asyncio
    async def test_find_by_iban_returns_mapping(
        self,
        mock_mapping_repo,
        sample_mapping,
    ):
        """Test finding mapping by IBAN."""
        mock_mapping_repo.find_by_iban.return_value = sample_mapping

        query = ListAccountMappingsQuery(mock_mapping_repo)
        result = await query.find_by_iban("DE89370400440532013000")

        assert result == sample_mapping
        mock_mapping_repo.find_by_iban.assert_called_once_with(
            "DE89370400440532013000",
        )

    @pytest.mark.asyncio
    async def test_find_by_iban_returns_none_when_not_found(self, mock_mapping_repo):
        """Test finding mapping returns None when not found."""
        mock_mapping_repo.find_by_iban.return_value = None

        query = ListAccountMappingsQuery(mock_mapping_repo)
        result = await query.find_by_iban("INVALID_IBAN")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_mapping_with_account_returns_both(
        self,
        mock_mapping_repo,
        mock_account_repo,
        sample_mapping,
    ):
        """Test getting mapping with resolved account."""
        mock_account = MagicMock()
        mock_account.name = "Checking"

        mock_mapping_repo.find_by_iban.return_value = sample_mapping
        mock_account_repo.find_by_id.return_value = mock_account

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.get_mapping_with_account("DE89370400440532013000")

        assert result is not None
        assert result.mapping == sample_mapping
        assert result.account == mock_account

    @pytest.mark.asyncio
    async def test_get_mapping_with_account_returns_none_when_mapping_not_found(
        self,
        mock_mapping_repo,
        mock_account_repo,
    ):
        """Test get_mapping_with_account returns None when mapping not found."""
        mock_mapping_repo.find_by_iban.return_value = None

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        result = await query.get_mapping_with_account("INVALID_IBAN")

        assert result is None
        mock_account_repo.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_mapping_with_account_without_account_repo(
        self,
        mock_mapping_repo,
        sample_mapping,
    ):
        """Test get_mapping_with_account works without account repo."""
        mock_mapping_repo.find_by_iban.return_value = sample_mapping

        # No account repo provided
        query = ListAccountMappingsQuery(mock_mapping_repo)
        result = await query.get_mapping_with_account("DE89370400440532013000")

        assert result is not None
        assert result.mapping == sample_mapping
        assert result.account is None

    @pytest.mark.asyncio
    async def test_get_all_with_accounts(
        self,
        mock_mapping_repo,
        mock_account_repo,
        sample_mapping,
    ):
        """Test getting all mappings with resolved accounts."""
        mock_account = MagicMock()
        mock_account.name = "Checking"

        mock_mapping_repo.find_all.return_value = [sample_mapping]
        mock_account_repo.find_by_id.return_value = mock_account

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)
        results = await query.get_all_with_accounts()

        assert len(results) == 1
        assert results[0].mapping == sample_mapping
        assert results[0].account == mock_account


class TestListAccountMappingsQueryDependencyInjection:
    """Tests to verify proper dependency injection."""

    def test_query_requires_mapping_repository(self):
        """Test that query requires a mapping repository."""
        mock_repo = AsyncMock()
        query = ListAccountMappingsQuery(mock_repo)
        assert query._mapping_repo is mock_repo

    def test_query_accepts_optional_account_repository(self):
        """Test that query accepts optional account repository."""
        mock_mapping_repo = AsyncMock()
        mock_account_repo = AsyncMock()

        query = ListAccountMappingsQuery(mock_mapping_repo, mock_account_repo)

        assert query._mapping_repo is mock_mapping_repo
        assert query._account_repo is mock_account_repo

    def test_query_works_without_account_repository(self):
        """Test that query works without account repository."""
        mock_mapping_repo = AsyncMock()

        query = ListAccountMappingsQuery(mock_mapping_repo)

        assert query._mapping_repo is mock_mapping_repo
        assert query._account_repo is None

