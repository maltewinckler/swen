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
    bank_account_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
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
        bank_account_import_service=bank_account_service,
        transfer_reconciliation_service=transfer_service,
        opening_balance_service=ob_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )

    return svc, {
        "bank_account_service": bank_account_service,
        "account_repo": account_repo,
        "transaction_repo": transaction_repo,
        "mapping_repo": mapping_repo,
        "import_repo": import_repo,
    }


# NOTE: Legacy test for import_transaction method removed
# The new flow uses import_from_stored_transactions which is tested
# in test_transaction_import_duplicates.py
