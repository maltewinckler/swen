"""Unit tests for ListImportsQuery."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.queries import ListImportsQuery
from swen.domain.integration.value_objects import ImportStatus


class TestListImportsQuery:
    """Tests for the ListImportsQuery.

    Note: ListImportsQuery uses user-scoped repositories, so no user_id
    parameter is needed in execute() - data is filtered automatically.
    """

    @pytest.fixture
    def mock_import_repo(self):
        """Create a mock import repository."""
        return AsyncMock()

    @pytest.fixture
    def sample_import(self):
        """Create a sample import for testing."""
        import_obj = MagicMock()
        import_obj.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        import_obj.status = ImportStatus.SUCCESS
        return import_obj

    @pytest.mark.asyncio
    async def test_execute_returns_imports_list(
        self,
        mock_import_repo,
        sample_import,
    ):
        """Test that execute returns a list of imports."""
        # Mock find_by_status to return sample import for SUCCESS only
        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [sample_import]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        assert result.total_count == 1
        assert len(result.imports) == 1
        assert result.imports[0] == sample_import

    @pytest.mark.asyncio
    async def test_execute_filters_by_date(self, mock_import_repo):
        """Test that execute filters imports by date."""
        old_import = MagicMock()
        old_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=60)
        old_import.status = ImportStatus.SUCCESS

        recent_import = MagicMock()
        recent_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        recent_import.status = ImportStatus.SUCCESS

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [old_import, recent_import]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        # Only recent import should be included
        assert result.total_count == 1
        assert result.imports[0] == recent_import

    @pytest.mark.asyncio
    async def test_execute_filters_by_iban(self, mock_import_repo, sample_import):
        """Test that execute filters imports by IBAN (placeholder - iban_filter unused)."""
        other_import = MagicMock()
        other_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        other_import.status = ImportStatus.SUCCESS

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [sample_import, other_import]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        # Note: iban_filter parameter exists but is not implemented yet
        result = await query.execute(
            days=30,
            limit=50,
            iban_filter="DE89370400440532013000",
        )

        # Both imports returned (iban_filter not implemented)
        assert result.total_count == 2

    @pytest.mark.asyncio
    async def test_execute_failed_only_flag(self, mock_import_repo):
        """Test that failed_only flag fetches only failed imports."""
        failed_import = MagicMock()
        failed_import.created_at = datetime.now(tz=timezone.utc)
        failed_import.status = ImportStatus.FAILED

        mock_import_repo.find_failed_imports.return_value = [failed_import]

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(
            days=30,
            limit=50,
            failed_only=True,
        )

        mock_import_repo.find_failed_imports.assert_called_once()
        assert result.total_count == 1
        assert result.imports[0].status == ImportStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_respects_limit(self, mock_import_repo):
        """Test that execute respects the limit parameter."""
        imports = []
        for i in range(10):
            imp = MagicMock()
            imp.created_at = datetime.now(tz=timezone.utc) - timedelta(hours=i)
            imp.status = ImportStatus.SUCCESS
            imports.append(imp)

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return imports
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=5)

        assert result.total_count == 5
        assert len(result.imports) <= 5

    @pytest.mark.asyncio
    async def test_execute_returns_status_counts(self, mock_import_repo):
        """Test that execute returns correct status counts."""
        success_import = MagicMock()
        success_import.created_at = datetime.now(tz=timezone.utc)
        success_import.status = ImportStatus.SUCCESS

        failed_import = MagicMock()
        failed_import.created_at = datetime.now(tz=timezone.utc)
        failed_import.status = ImportStatus.FAILED

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [success_import]
            if status == ImportStatus.FAILED:
                return [failed_import]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        # Status counts use status.value which is the enum value string
        assert len(result.status_counts) == 2
        assert result.total_count == 2

    @pytest.mark.asyncio
    async def test_get_status_statistics(self, mock_import_repo):
        """Test getting overall statistics."""
        mock_import_repo.count_by_status.return_value = {
            "SUCCESS": 100,
            "FAILED": 5,
            "DUPLICATE": 10,
        }

        query = ListImportsQuery(mock_import_repo)
        result = await query.get_status_statistics()

        assert result == {"SUCCESS": 100, "FAILED": 5, "DUPLICATE": 10}
        mock_import_repo.count_by_status.assert_called_once()
