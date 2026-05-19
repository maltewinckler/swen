"""Tests for the TransactionImportService orchestration helpers."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from swen.application.factories import BankImportTransactionFactory
from swen.application.integration.services import TransactionImportService
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.integration.services import (
    TransferReconciliationService,
)
from swen.domain.shared.current_user import CurrentUser

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def service():
    """Create a TransactionImportService with mocked dependencies."""
    import_repo = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    ob_service = OpeningBalanceService(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        user_id=TEST_USER_ID,
    )
    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
    )

    transaction_factory = BankImportTransactionFactory(
        current_user=current_user,
    )

    svc = TransactionImportService(
        bank_account_import_service=AsyncMock(),
        transfer_reconciliation_service=transfer_service,
        opening_balance_service=ob_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )
    return svc, import_repo
