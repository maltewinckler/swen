"""Tests for the TransactionImportService orchestration helpers."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from swen.application.context import UserContext
from swen.application.factories import BankImportTransactionFactory
from swen.application.services import TransactionImportService
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def service():
    """Create a TransactionImportService with mocked dependencies."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    user_context = UserContext(user_id=TEST_USER_ID, email="test@example.com")

    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )

    transaction_factory = BankImportTransactionFactory(
        user_context=user_context,
    )

    svc = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        user_context=user_context,
    )

    return svc, {
        "bank_account_service": bank_account_service,
        "counter_account_resolution_service": counter_account_resolution_service,
        "account_repo": account_repo,
        "transaction_repo": transaction_repo,
        "mapping_repo": mapping_repo,
        "import_repo": import_repo,
    }


@pytest.mark.asyncio
async def test_get_import_statistics_aggregates_counts(service):
    """Statistics should use repository counts and include totals."""
    svc, deps = service
    import_repo = deps["import_repo"]
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
    svc, deps = service
    import_repo = deps["import_repo"]
    import_repo.count_by_status.return_value = {"success": 2}

    stats = await svc.get_import_statistics(iban="DE89...")

    assert stats["success"] == 2
    assert stats["failed"] == 0
    assert stats["pending"] == 0
    assert stats["duplicate"] == 0
    assert stats["skipped"] == 0
    assert stats["total"] == 2
    import_repo.count_by_status.assert_awaited_once_with("DE89...")

    # NOTE: Legacy test for import_transaction method removed
    # The new flow uses import_from_stored_transactions which is tested
    # in test_transaction_import_duplicates.py
