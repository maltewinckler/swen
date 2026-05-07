"""Tests for TransactionImportService atomic persistence behavior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from swen.application.factories import BankImportTransactionFactory
from swen.application.services import TransactionImportService
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.services import (
    TransferReconciliationService,
)
from swen.domain.integration.value_objects import ImportStatus, ResolutionResult
from swen.domain.shared.current_user import CurrentUser

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _stored(tx: BankTransaction) -> StoredBankTransaction:
    return StoredBankTransaction(
        id=uuid4(),
        identity_hash=tx.compute_identity_hash("DE89370400440532013000"),
        hash_sequence=1,
        transaction=tx,
        is_imported=False,
        is_new=True,
    )


@pytest.mark.asyncio
async def test_import_persists_success_atomically():
    """Persistence should use save_complete_import for atomic writes."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    asset_account = Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number="1200",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
        iban="DE89370400440532013000",
    )
    income_account = Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="3000",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )
    bank_account_service.get_or_create_asset_account.return_value = asset_account
    mapping_repo.find_by_iban.return_value = None
    import_repo.find_by_bank_transaction_id.return_value = None

    resolution_result = MagicMock(spec=ResolutionResult)
    resolution_result.account = income_account
    resolution_result.has_ai_result = False
    counter_account_resolution_service.resolve_counter_account_with_details.return_value = resolution_result

    ob_service = OpeningBalanceService(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        user_id=TEST_USER_ID,
    )
    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
        opening_balance_query=ob_service,
    )
    transaction_factory = BankImportTransactionFactory(current_user=current_user)

    svc = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        opening_balance_service=ob_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )

    tx = BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("10.00"),
        currency="EUR",
        purpose="Salary",
    )

    results = []
    async for _, _, result in svc.import_streaming(
        stored_transactions=[_stored(tx)],
        source_iban="DE89370400440532013000",
        preclassified={},
        auto_post=False,
    ):
        results.append(result)

    assert results[0].status == ImportStatus.SUCCESS
    # Atomicity is contracted by save_complete_import on the repository
    import_repo.save_complete_import.assert_awaited_once()
    call_kwargs = import_repo.save_complete_import.await_args.kwargs
    assert call_kwargs["accounting_tx"] is not None
    assert call_kwargs["import_record"] is not None


@pytest.mark.asyncio
async def test_import_uses_save_complete_import_for_persistence():
    """Persistence always goes through save_complete_import regardless of any external state."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    asset_account = Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number="1200",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
        iban="DE89370400440532013000",
    )
    income_account = Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="3000",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )
    bank_account_service.get_or_create_asset_account.return_value = asset_account
    mapping_repo.find_by_iban.return_value = None
    import_repo.find_by_bank_transaction_id.return_value = None

    resolution_result = MagicMock(spec=ResolutionResult)
    resolution_result.account = income_account
    resolution_result.has_ai_result = False
    counter_account_resolution_service.resolve_counter_account_with_details.return_value = resolution_result

    ob_service = OpeningBalanceService(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        user_id=TEST_USER_ID,
    )
    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
        opening_balance_query=ob_service,
    )
    transaction_factory = BankImportTransactionFactory(current_user=current_user)

    svc = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        opening_balance_service=ob_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
    )

    tx = BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("10.00"),
        currency="EUR",
        purpose="Salary",
    )

    results = []
    async for _, _, result in svc.import_streaming(
        stored_transactions=[_stored(tx)],
        source_iban="DE89370400440532013000",
        preclassified={},
        auto_post=False,
    ):
        results.append(result)

    assert results[0].status == ImportStatus.SUCCESS
    # Persistence goes through save_complete_import
    import_repo.save_complete_import.assert_awaited_once()
