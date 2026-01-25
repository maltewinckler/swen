"""Unit tests for TransactionSyncCommand."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from swen.application.commands.integration import TransactionSyncCommand
from swen.application.ports.identity import CurrentUser
from swen.domain.banking.value_objects import BankCredentials, TANChallenge
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.time import today_utc
from swen.domain.shared.value_objects.secure_string import SecureString

IBAN = "DE89370400440532013000"
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_credentials() -> BankCredentials:
    return BankCredentials(
        blz="50031000",
        username=SecureString("user"),
        pin=SecureString("123456"),
        endpoint="https://fints.example.com/fints",
    )


def _make_mapping(active: bool = True) -> AccountMapping:
    return AccountMapping(
        iban=IBAN,
        accounting_account_id=uuid4(),
        account_name="Test Account",
        user_id=TEST_USER_ID,
        is_active=active,
    )


def _make_stored_transaction(is_new: bool = True, is_imported: bool = False):
    """Create a mock StoredBankTransaction for testing.

    Args:
        is_new: Whether transaction was just stored (True) or already existed (False)
        is_imported: Whether transaction has been imported to accounting (True) or not (False)
    """
    return SimpleNamespace(
        id=uuid4(),
        identity_hash="test_hash",
        hash_sequence=1,
        transaction=SimpleNamespace(
            booking_date=date(2024, 1, 15),
            amount=-50.00,
            purpose="Test transaction",
            applicant_iban=None,
        ),
        is_imported=is_imported,
        is_new=is_new,
    )


def _make_command():
    adapter = AsyncMock()
    adapter.is_connected = Mock(return_value=False)
    adapter.set_tan_callback = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.fetch_transactions = AsyncMock()
    adapter.disconnect = AsyncMock()

    import_service = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    bank_transaction_repo = AsyncMock()

    # Default: empty stored results (will be overridden by tests)
    bank_transaction_repo.save_batch_with_deduplication.return_value = []

    # Create user context
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    command = TransactionSyncCommand(
        bank_adapter=adapter,
        import_service=import_service,
        mapping_repo=mapping_repo,
        import_repo=import_repo,
        current_user=current_user,
        bank_transaction_repo=bank_transaction_repo,
    )

    return (
        command,
        adapter,
        import_service,
        mapping_repo,
        import_repo,
        bank_transaction_repo,
    )


@pytest.mark.asyncio
async def test_execute_fails_when_mapping_missing():
    command, adapter, import_service, mapping_repo, _, _bank_tx_repo = _make_command()
    mapping_repo.find_by_iban.return_value = None

    result = await command.execute(iban=IBAN, credentials=_make_credentials())

    assert result.success is False
    assert result.error_message is not None
    assert "No active account mapping" in result.error_message
    adapter.connect.assert_not_called()
    import_service.import_from_stored_transactions.assert_not_called()


@pytest.mark.asyncio
async def test_execute_uses_history_for_default_start_date():
    (
        command,
        adapter,
        _import_service,
        mapping_repo,
        import_repo,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    history = [
        SimpleNamespace(
            status=ImportStatus.FAILED,
            bank_transaction_id=uuid4(),
            imported_at=datetime(2024, 1, 8, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            status=ImportStatus.SUCCESS,
            bank_transaction_id=uuid4(),
            imported_at=datetime(2024, 1, 11, tzinfo=timezone.utc),
        ),
    ]
    import_repo.find_by_iban.return_value = history

    adapter.fetch_transactions.return_value = []
    bank_tx_repo.save_batch_with_deduplication.return_value = []

    today = today_utc()
    result = await command.execute(iban=IBAN, credentials=_make_credentials())

    # Start date is last import date + 1 day
    assert result.start_date == date(2024, 1, 12)
    assert result.end_date == today
    adapter.fetch_transactions.assert_awaited_once_with(
        account_iban=IBAN,
        start_date=date(2024, 1, 12),
        end_date=today,
    )


@pytest.mark.asyncio
async def test_default_start_date_clamped_to_today_when_last_import_today():
    (
        command,
        adapter,
        _import_service,
        mapping_repo,
        import_repo,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    today = today_utc()
    import_repo.find_by_iban.return_value = [
        SimpleNamespace(
            status=ImportStatus.SUCCESS,
            bank_transaction_id=uuid4(),
            imported_at=datetime.combine(
                today,
                datetime.min.time(),
                tzinfo=timezone.utc,
            ),
        ),
    ]

    adapter.fetch_transactions.return_value = []
    bank_tx_repo.save_batch_with_deduplication.return_value = []

    result = await command.execute(iban=IBAN, credentials=_make_credentials())

    assert result.start_date == today
    assert result.end_date == today


@pytest.mark.asyncio
async def test_execute_counts_results_and_sets_warning_on_partial_failure():
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        _,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    # Simulate 4 transactions fetched from bank
    adapter.fetch_transactions.return_value = [SimpleNamespace() for _ in range(4)]

    # All 4 are new (stored)
    stored_txs = [_make_stored_transaction(is_new=True) for _ in range(4)]
    bank_tx_repo.save_batch_with_deduplication.return_value = stored_txs

    # Import results: 2 success, 1 skipped, 1 failed
    import_service.import_from_stored_transactions.return_value = [
        SimpleNamespace(status=ImportStatus.SUCCESS),
        SimpleNamespace(status="imported"),
        SimpleNamespace(status="skipped_duplicate"),
        SimpleNamespace(status="failed"),
    ]

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    assert result.success is True
    assert result.warning_message == "1 transaction failed to import"
    assert result.error_message is None
    assert result.transactions_imported == 2
    assert result.transactions_skipped == 1
    assert result.transactions_failed == 1
    assert result.transactions_fetched == 4
    adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_returns_error_when_all_imports_fail():
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        _,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    adapter.fetch_transactions.return_value = [SimpleNamespace(), SimpleNamespace()]

    # 2 new transactions stored
    stored_txs = [_make_stored_transaction(is_new=True) for _ in range(2)]
    bank_tx_repo.save_batch_with_deduplication.return_value = stored_txs

    import_service.import_from_stored_transactions.return_value = [
        SimpleNamespace(status="failed"),
        SimpleNamespace(status=ImportStatus.FAILED),
    ]

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 28),
    )

    assert result.success is False
    assert result.error_message == "2 transactions failed to import"
    assert result.warning_message is None
    assert result.transactions_imported == 0
    assert result.transactions_failed == 2
    adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_tan_callback_is_wrapped_before_connect():
    (
        command,
        adapter,
        _import_service,
        mapping_repo,
        _,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    adapter.fetch_transactions.return_value = []
    bank_tx_repo.save_batch_with_deduplication.return_value = []

    def tan_callback(_challenge: TANChallenge) -> str:
        return "123456"

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        tan_callback=tan_callback,
    )

    assert result.success is True
    adapter.set_tan_callback.assert_awaited_once()
    adapter.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_disconnects_even_on_fetch_failure():
    (
        command,
        adapter,
        _import_service,
        mapping_repo,
        _,
        _bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    adapter.fetch_transactions.side_effect = RuntimeError("Network error")

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 31),
    )

    assert result.success is False
    assert result.error_message is not None
    assert "Network error" in result.error_message
    adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_returns_success_when_all_transactions_already_imported():
    """
    Test that sync succeeds without calling import when all transactions
    are already stored AND imported.

    Note: Transactions that are stored but NOT imported will still be imported
    (this handles cases where a previous sync failed during import).
    """
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        _,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    # 3 transactions fetched, all already stored AND imported
    adapter.fetch_transactions.return_value = [SimpleNamespace() for _ in range(3)]
    bank_tx_repo.save_batch_with_deduplication.return_value = [
        _make_stored_transaction(is_new=False, is_imported=True),
        _make_stored_transaction(is_new=False, is_imported=True),
        _make_stored_transaction(is_new=False, is_imported=True),
    ]

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 30),
    )

    assert result.success is True
    assert result.transactions_fetched == 3
    assert result.transactions_imported == 0
    # import_from_stored_transactions should NOT be called when all are imported
    import_service.import_from_stored_transactions.assert_not_called()
    adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_retries_unimported_transactions():
    """
    Test that stored transactions that were NOT imported (from a previous failed sync)
    are retried and imported on subsequent syncs.

    This handles the case where:
    1. First sync stores transactions but fails during import
    2. Second sync should retry importing those transactions
    """
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        _,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    # 3 transactions fetched, all already stored but NOT imported
    adapter.fetch_transactions.return_value = [SimpleNamespace() for _ in range(3)]
    bank_tx_repo.save_batch_with_deduplication.return_value = [
        _make_stored_transaction(is_new=False, is_imported=False),
        _make_stored_transaction(is_new=False, is_imported=False),
        _make_stored_transaction(is_new=False, is_imported=False),
    ]

    # Mock successful imports
    import_service.import_from_stored_transactions.return_value = [
        SimpleNamespace(status=ImportStatus.SUCCESS),
        SimpleNamespace(status=ImportStatus.SUCCESS),
        SimpleNamespace(status=ImportStatus.SUCCESS),
    ]

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 30),
    )

    assert result.success is True
    assert result.transactions_fetched == 3
    assert result.transactions_imported == 3
    # import_from_stored_transactions SHOULD be called for unimported transactions
    import_service.import_from_stored_transactions.assert_awaited_once()
    adapter.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_result_tracks_all_statistics():
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        import_repo,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()

    import_repo.find_by_iban.return_value = []

    adapter.fetch_transactions.return_value = [SimpleNamespace() for _ in range(3)]

    # 2 new, 1 already stored
    bank_tx_repo.save_batch_with_deduplication.return_value = [
        _make_stored_transaction(is_new=True),
        _make_stored_transaction(is_new=True),
        _make_stored_transaction(is_new=False),
    ]

    import_service.import_from_stored_transactions.return_value = [
        SimpleNamespace(status=ImportStatus.SUCCESS),
        SimpleNamespace(status=ImportStatus.SUCCESS),
    ]

    result = await command.execute(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
    )

    assert result.success is True
    assert result.transactions_fetched == 3
    assert result.transactions_imported == 2
    assert result.transactions_failed == 0


# =============================================================================
# Streaming tests (execute_streaming)
# =============================================================================


def _make_mock_transaction_with_entries():
    """Create a mock Transaction with entries for streaming test.

    Entry ordering (from BankImportTransactionFactory):
    - entries[0] = counter_account (expense/income category like "Lebensmittel")
    - entries[1] = asset_account (bank account like "Girokonto")
    """
    from decimal import Decimal

    from swen.domain.accounting.value_objects import Money

    # Create mock accounts
    bank_account = Mock()
    bank_account.name = "Girokonto"
    bank_account.id = uuid4()

    counter_account = Mock()
    counter_account.name = "Lebensmittel"
    counter_account.id = uuid4()

    # Create mock entries (order matters: counter_account first, then bank_account)
    debit_entry = Mock()  # Counter account (expense)
    debit_entry.account = counter_account
    debit_entry.debit = Money(Decimal("50.00"))
    debit_entry.credit = Money(Decimal("0"))

    credit_entry = Mock()  # Bank account
    credit_entry.account = bank_account
    credit_entry.debit = Money(Decimal("0"))
    credit_entry.credit = Money(Decimal("50.00"))

    # Create mock transaction with entries property (not journal_entries!)
    # Order: [counter_account entry, bank_account entry]
    transaction = Mock()
    transaction.id = uuid4()
    transaction.entries = [debit_entry, credit_entry]

    return transaction


@pytest.mark.asyncio
async def test_execute_streaming_emits_transaction_classified_events():
    """
    Test that execute_streaming emits TransactionClassifiedEvent with counter account name.

    This test would have caught the bug where `journal_entries` was used instead of `entries`.
    """
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        import_repo,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()
    import_repo.find_by_iban.return_value = []

    # Simulate 1 transaction fetched from bank
    adapter.fetch_transactions.return_value = [SimpleNamespace()]

    # 1 new transaction stored
    stored_tx = _make_stored_transaction(is_new=True)
    bank_tx_repo.save_batch_with_deduplication.return_value = [stored_tx]

    # Create mock import result with a proper Transaction that has entries
    mock_transaction = _make_mock_transaction_with_entries()

    import_result = SimpleNamespace(
        status=ImportStatus.SUCCESS,
        accounting_transaction=mock_transaction,
        bank_transaction=SimpleNamespace(purpose="REWE Supermarkt"),
    )

    # Mock the streaming import method
    async def mock_import_streaming(*args, **kwargs):
        yield (1, 1, import_result)

    import_service.import_from_stored_transactions_streaming = mock_import_streaming

    # Collect events from streaming
    from swen.application.dtos.integration import TransactionClassifiedEvent

    events = []
    async for event in command.execute_streaming(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30),
    ):
        events.append(event)

    # Find TransactionClassifiedEvent in the events
    classified_events = [e for e in events if isinstance(e, TransactionClassifiedEvent)]

    assert len(classified_events) == 1
    assert classified_events[0].counter_account_name == "Lebensmittel"
    assert classified_events[0].description == "REWE Supermarkt"


@pytest.mark.asyncio
async def test_execute_streaming_handles_missing_transaction():
    """
    Test that execute_streaming handles cases where accounting_transaction is None.
    """
    (
        command,
        adapter,
        import_service,
        mapping_repo,
        import_repo,
        bank_tx_repo,
    ) = _make_command()
    mapping_repo.find_by_iban.return_value = _make_mapping()
    import_repo.find_by_iban.return_value = []

    adapter.fetch_transactions.return_value = [SimpleNamespace()]

    stored_tx = _make_stored_transaction(is_new=True)
    bank_tx_repo.save_batch_with_deduplication.return_value = [stored_tx]

    # Import result with no accounting_transaction
    import_result = SimpleNamespace(
        status=ImportStatus.SUCCESS,
        accounting_transaction=None,
        bank_transaction=SimpleNamespace(purpose="Unknown transaction"),
    )

    async def mock_import_streaming(*args, **kwargs):
        yield (1, 1, import_result)

    import_service.import_from_stored_transactions_streaming = mock_import_streaming

    from swen.application.dtos.integration import TransactionClassifiedEvent

    events = []
    async for event in command.execute_streaming(
        iban=IBAN,
        credentials=_make_credentials(),
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 31),
    ):
        events.append(event)

    classified_events = [e for e in events if isinstance(e, TransactionClassifiedEvent)]

    assert len(classified_events) == 1
    # Counter account name should be empty when no transaction
    assert classified_events[0].counter_account_name == ""
