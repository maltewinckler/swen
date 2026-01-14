"""Tests for TransactionImportService atomic persistence behavior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from swen.application.factories import BankImportTransactionFactory
from swen.application.services import TransactionImportService
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import ImportStatus, ResolutionResult
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_transaction_repository import (
    StoredBankTransaction,
)
from swen.application.ports.identity import CurrentUser

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class _BeginContext:
    def __init__(self, session: "_FakeSession"):
        self._session = session

    async def __aenter__(self):
        self._session._in_tx = True
        self._session.begin_entered += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._session._in_tx = False
        self._session.begin_exited += 1
        return False


class _FakeSession:
    def __init__(self, in_tx: bool = False):
        self._in_tx = in_tx
        self.begin_called = 0
        self.begin_entered = 0
        self.begin_exited = 0

    def in_transaction(self) -> bool:
        return self._in_tx

    def begin(self):
        self.begin_called += 1
        return _BeginContext(self)


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
async def test_import_persists_success_atomically_when_session_provided():
    """When a session is provided, success persistence should run inside session.begin()."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")
    fake_session = _FakeSession(in_tx=False)

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
    counter_account_resolution_service.resolve_counter_account_with_details.return_value = (
        resolution_result
    )

    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )
    transaction_factory = BankImportTransactionFactory(current_user=current_user)

    svc = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
        db_session=fake_session,  # type: ignore[arg-type]  # test double
    )

    tx = BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("10.00"),
        currency="EUR",
        purpose="Salary",
    )

    results = await svc.import_from_stored_transactions(
        stored_transactions=[_stored(tx)],
        source_iban="DE89370400440532013000",
        auto_post=False,
    )

    assert results[0].status == ImportStatus.SUCCESS
    assert fake_session.begin_called == 1
    assert fake_session.begin_entered == 1
    assert fake_session.begin_exited == 1
    transaction_repo.save.assert_awaited()
    import_repo.save.assert_awaited()


@pytest.mark.asyncio
async def test_import_does_not_start_nested_transaction_when_already_in_transaction():
    """If session.in_transaction() is True, TransactionImportService should not call begin()."""
    bank_account_service = AsyncMock()
    counter_account_resolution_service = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")
    fake_session = _FakeSession(in_tx=True)

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
    counter_account_resolution_service.resolve_counter_account_with_details.return_value = (
        resolution_result
    )

    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )
    transaction_factory = BankImportTransactionFactory(current_user=current_user)

    svc = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=current_user,
        db_session=fake_session,  # type: ignore[arg-type]  # test double
    )

    tx = BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("10.00"),
        currency="EUR",
        purpose="Salary",
    )

    results = await svc.import_from_stored_transactions(
        stored_transactions=[_stored(tx)],
        source_iban="DE89370400440532013000",
        auto_post=False,
    )

    assert results[0].status == ImportStatus.SUCCESS
    assert fake_session.begin_called == 0
    transaction_repo.save.assert_awaited()
    import_repo.save.assert_awaited()
