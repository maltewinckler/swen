"""Tests for the TransactionImportService orchestration helpers."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from swen.application.factories import BankImportTransactionFactory
from swen.application.ports.identity import CurrentUser
from swen.application.queries.integration import OpeningBalanceQuery
from swen.application.services import TransactionImportService
from swen.application.services.opening_balance_adjustment_service import (
    OpeningBalanceAdjustmentService,
)
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def service():
    """Create a TransactionImportService with mocked dependencies."""
    import_repo = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    ob_query = OpeningBalanceQuery(transaction_repository=transaction_repo)
    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
        opening_balance_query=ob_query,
    )

    transaction_factory = BankImportTransactionFactory(
        current_user=current_user,
    )

    ob_adjustment_service = OpeningBalanceAdjustmentService(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        opening_balance_query=ob_query,
        current_user=current_user,
    )

    svc = TransactionImportService(
        bank_account_import_service=AsyncMock(),
        counter_account_resolution_service=AsyncMock(),
        transfer_reconciliation_service=transfer_service,
        opening_balance_adjustment_service=ob_adjustment_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )
    return svc, import_repo


@pytest.mark.asyncio
async def test_get_import_statistics_aggregates_counts(service):
    """Statistics should use repository counts and include totals."""
    svc, import_repo = service
    import_repo.count_by_status.return_value = {
        "success": 5,
        "failed": 1,
        "pending": 2,
        "duplicate": 3,
        "skipped": 4,
    }

    stats = await svc.get_import_statistics()

    assert stats == {
        "success": 5,
        "failed": 1,
        "pending": 2,
        "duplicate": 3,
        "skipped": 4,
        "total": 15,
    }
    import_repo.count_by_status.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_get_import_statistics_defaults_missing_statuses(service):
    """Missing status buckets should default to zero and forward IBAN filters."""
    svc, import_repo = service
    import_repo.count_by_status.return_value = {"success": 2}

    stats = await svc.get_import_statistics(iban="DE89...")

    assert stats["success"] == 2
    assert stats["failed"] == 0
    assert stats["pending"] == 0
    assert stats["duplicate"] == 0
    assert stats["skipped"] == 0
    assert stats["total"] == 2
    import_repo.count_by_status.assert_awaited_once_with("DE89...")
