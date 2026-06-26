"""Unit tests for ListImportsQuery."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.integration.queries import ListImportsQuery
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
        import_obj.id = uuid4()
        import_obj.bank_transaction_id = uuid4()
        import_obj.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        import_obj.status = ImportStatus.SUCCESS
        import_obj.error_message = None
        import_obj.accounting_transaction_id = uuid4()
        import_obj.imported_at = datetime.now(tz=timezone.utc) - timedelta(
            days=5, seconds=1
        )
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

        assert result.count == 1
        assert len(result.imports) == 1
        assert result.imports[0].status == "success"

    @pytest.mark.asyncio
    async def test_execute_filters_by_date(self, mock_import_repo):
        """Test that execute filters imports by date."""
        old_import = MagicMock()
        old_import.id = uuid4()
        old_import.bank_transaction_id = uuid4()
        old_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=60)
        old_import.status = ImportStatus.SUCCESS
        old_import.error_message = None
        old_import.accounting_transaction_id = None
        old_import.imported_at = None

        recent_import = MagicMock()
        recent_import.id = uuid4()
        recent_import.bank_transaction_id = uuid4()
        recent_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        recent_import.status = ImportStatus.SUCCESS
        recent_import.error_message = None
        recent_import.accounting_transaction_id = None
        recent_import.imported_at = None

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [old_import, recent_import]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        # Only recent import should be included
        assert result.count == 1
        assert result.imports[0].status == "success"

    @pytest.mark.asyncio
    async def test_execute_filters_by_iban(
        self,
        mock_import_repo,
        sample_import,
    ):
        """Test that execute filters imports by IBAN (placeholder - iban_filter unused)."""
        other_import = MagicMock()
        other_import.id = uuid4()
        other_import.bank_transaction_id = uuid4()
        other_import.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        other_import.status = ImportStatus.SUCCESS
        other_import.error_message = None
        other_import.accounting_transaction_id = None
        other_import.imported_at = None

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
        assert result.count == 2

    @pytest.mark.asyncio
    async def test_execute_failed_only_flag(self, mock_import_repo):
        """Test that failed_only flag fetches only failed imports."""
        failed_import = MagicMock()
        failed_import.id = uuid4()
        failed_import.bank_transaction_id = uuid4()
        failed_import.created_at = datetime.now(tz=timezone.utc)
        failed_import.status = ImportStatus.FAILED
        failed_import.error_message = "Something went wrong"
        failed_import.accounting_transaction_id = None
        failed_import.imported_at = None

        mock_import_repo.find_failed_imports.return_value = [failed_import]

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(
            days=30,
            limit=50,
            failed_only=True,
        )

        mock_import_repo.find_failed_imports.assert_called_once()
        assert result.count == 1
        assert result.imports[0].status == "failed"
        assert result.imports[0].error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_execute_respects_limit(self, mock_import_repo):
        """Test that execute respects the limit parameter."""
        imports = []
        for i in range(10):
            imp = MagicMock()
            imp.id = uuid4()
            imp.bank_transaction_id = uuid4()
            imp.created_at = datetime.now(tz=timezone.utc) - timedelta(hours=i)
            imp.status = ImportStatus.SUCCESS
            imp.error_message = None
            imp.accounting_transaction_id = None
            imp.imported_at = None
            imports.append(imp)

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return imports
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=5)

        assert result.count == 5
        assert len(result.imports) <= 5

    @pytest.mark.asyncio
    async def test_execute_returns_status_counts(self, mock_import_repo):
        """Test that execute returns correct status counts."""
        success_import = MagicMock()
        success_import.id = uuid4()
        success_import.bank_transaction_id = uuid4()
        success_import.created_at = datetime.now(tz=timezone.utc)
        success_import.status = ImportStatus.SUCCESS
        success_import.error_message = None
        success_import.accounting_transaction_id = None
        success_import.imported_at = None

        failed_import = MagicMock()
        failed_import.id = uuid4()
        failed_import.bank_transaction_id = uuid4()
        failed_import.created_at = datetime.now(tz=timezone.utc)
        failed_import.status = ImportStatus.FAILED
        failed_import.error_message = "Error"
        failed_import.accounting_transaction_id = None
        failed_import.imported_at = None

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
        assert result.count == 2

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list(self, mock_import_repo):
        """Test that execute returns empty list when no imports exist."""
        mock_import_repo.find_by_status.return_value = []

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        assert result.count == 0
        assert result.imports == []
        assert result.status_counts == {}

    @pytest.mark.asyncio
    async def test_execute_dto_has_correct_fields(self, mock_import_repo):
        """Test that the DTO has all expected fields."""
        sample = MagicMock()
        sample.id = uuid4()
        sample.bank_transaction_id = uuid4()
        sample.created_at = datetime.now(tz=timezone.utc)
        sample.status = ImportStatus.SUCCESS
        sample.error_message = None
        sample.accounting_transaction_id = uuid4()
        sample.imported_at = datetime.now(tz=timezone.utc)

        async def mock_find_by_status(status):
            if status == ImportStatus.SUCCESS:
                return [sample]
            return []

        mock_import_repo.find_by_status.side_effect = mock_find_by_status

        query = ListImportsQuery(mock_import_repo)
        result = await query.execute(days=30, limit=50)

        dto = result.imports[0]
        assert dto.id == sample.id
        assert dto.bank_transaction_id == sample.bank_transaction_id
        assert dto.status == "success"
        assert dto.error_message is None
        assert dto.transaction_id == sample.accounting_transaction_id
        assert dto.created_at == sample.created_at
        assert dto.imported_at == sample.imported_at
