"""Unit tests for SyncStatusQuery.

Note: SyncStatusQuery uses user-scoped repositories, so no user_id
parameter is needed - the repository handles user filtering.
"""

from unittest.mock import AsyncMock

import pytest

from swen.application.queries import SyncStatusQuery


class TestSyncStatusQuery:
    """Tests for the SyncStatusQuery."""

    @pytest.fixture
    def mock_import_repo(self):
        """Create a mock import repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_execute_returns_all_status_counts(self, mock_import_repo):
        """Test that execute returns all status counts."""
        # ImportStatus enum values are lowercase
        mock_import_repo.count_by_status.return_value = {
            "success": 100,
            "failed": 5,
            "pending": 2,
            "duplicate": 10,
            "skipped": 3,
        }

        query = SyncStatusQuery(mock_import_repo)
        result = await query.execute()

        assert result.success_count == 100
        assert result.failed_count == 5
        assert result.pending_count == 2
        assert result.duplicate_count == 10
        assert result.skipped_count == 3
        assert result.total_count == 120

    @pytest.mark.asyncio
    async def test_execute_handles_missing_statuses(self, mock_import_repo):
        """Test that execute handles missing status counts."""
        # ImportStatus enum values are lowercase
        mock_import_repo.count_by_status.return_value = {
            "success": 50,
        }

        query = SyncStatusQuery(mock_import_repo)
        result = await query.execute()

        assert result.success_count == 50
        assert result.failed_count == 0
        assert result.pending_count == 0
        assert result.duplicate_count == 0
        assert result.skipped_count == 0
        assert result.total_count == 50

    @pytest.mark.asyncio
    async def test_execute_handles_empty_counts(self, mock_import_repo):
        """Test that execute handles empty result."""
        mock_import_repo.count_by_status.return_value = {}

        query = SyncStatusQuery(mock_import_repo)
        result = await query.execute()

        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_execute_delegates_to_repository(self, mock_import_repo):
        """Test that execute delegates to repository."""
        mock_import_repo.count_by_status.return_value = {}

        query = SyncStatusQuery(mock_import_repo)
        await query.execute()

        mock_import_repo.count_by_status.assert_called_once()


class TestSyncStatusQueryDependencyInjection:
    """Tests to verify proper dependency injection."""

    def test_query_requires_repository(self):
        """Test that query requires an import repository."""
        mock_repo = AsyncMock()
        query = SyncStatusQuery(mock_repo)
        assert query._import_repo is mock_repo

    @pytest.mark.asyncio
    async def test_query_delegates_all_operations(self):
        """Test that query delegates to repository."""
        mock_repo = AsyncMock()
        mock_repo.count_by_status.return_value = {"SUCCESS": 10}

        query = SyncStatusQuery(mock_repo)
        await query.execute()

        mock_repo.count_by_status.assert_called_once()
