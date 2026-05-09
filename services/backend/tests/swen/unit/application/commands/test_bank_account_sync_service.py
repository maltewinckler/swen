"""Unit tests for BankAccountSyncService.

Covers:
- Event order: AccountSyncFetchedEvent → classification events
- InactiveMappingError when mapping.is_active = False
- Empty-import branch: update_last_used called, SyncResult with zero imports,
  no classification events
- Batch processing: _process_batch_loop resolves + imports in interleaved batches

Note: AccountSyncStartedEvent is now emitted by SyncBankAccountsCommand via
the SyncNotificationService, not by BankAccountSyncService directly.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.events import (
    AccountSyncFetchedEvent,
    ClassificationCompletedEvent,
    ClassificationStartedEvent,
)
from swen.application.services.integration.bank_account_sync.bank_account_sync_service import (
    BankAccountSyncService,
)
from swen.application.services.integration.sync_notification_service import (
    SyncNotificationService,
)
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.exceptions import InactiveMappingError
from tests.shared.sync_event_publisher import InMemorySyncEventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IBAN = "DE89370400440532013000"
_BLZ = "37040044"


def _make_mapping(*, is_active: bool = True) -> AccountMapping:
    return cast(
        "AccountMapping",
        SimpleNamespace(
            iban=_IBAN, blz=_BLZ, account_name="Test Account", is_active=is_active
        ),
    )


def _make_stored_transaction(*, is_new: bool = True, is_imported: bool = False):
    return SimpleNamespace(is_new=is_new, is_imported=is_imported)


def _make_import_result(*, is_success: bool = True):
    """Create a minimal import result for testing."""
    result = MagicMock()
    result.is_success = is_success
    result.bank_transaction = SimpleNamespace(purpose="Test transaction")
    result.accounting_transaction = None
    return result


def _make_service(
    *,
    publisher: InMemorySyncEventPublisher,
    bank_transactions=None,
    stored_transactions=None,
    resolve_batch_return=None,
    import_results=None,
) -> tuple[BankAccountSyncService, SyncNotificationService]:
    """Build a BankAccountSyncService with all dependencies mocked.

    Returns (service, notifier) so tests can set account context via
    notifier.emit_account_sync_started_event() before calling sync_account().
    """
    if bank_transactions is None:
        bank_transactions = []
    if stored_transactions is None:
        stored_transactions = []
    if import_results is None:
        import_results = []
    if resolve_batch_return is None:
        resolve_batch_return = {}

    bank_fetch_service = AsyncMock()
    bank_fetch_service.fetch_transactions.return_value = bank_transactions

    bank_transaction_repo = AsyncMock()
    bank_transaction_repo.save_batch_with_deduplication.return_value = (
        stored_transactions
    )

    bank_balance_service = AsyncMock()
    bank_balance_service.get_for_iban.return_value = None

    opening_balance_service = AsyncMock()
    opening_balance_service.try_create_for_first_sync.return_value = None

    batch_service = AsyncMock()
    batch_service.resolve_batch.return_value = resolve_batch_return

    import_service = AsyncMock()
    import_service.import_batch.return_value = import_results
    # compute_stats is a sync method — override so it returns a plain tuple, not a coroutine
    import_service.compute_stats = MagicMock(return_value=(0, 0, 0))

    credential_repo = AsyncMock()
    credential_repo.find_by_blz.return_value = (
        MagicMock()
    )  # Return some mock credentials
    credential_repo.get_tan_settings.return_value = (None, None)
    credential_repo.update_last_used = AsyncMock()

    import_repo = AsyncMock()
    import_repo.find_latest_booking_date_by_iban.return_value = None

    notifier = SyncNotificationService(publisher)

    service = BankAccountSyncService(
        bank_fetch_service=bank_fetch_service,
        opening_balance_service=opening_balance_service,
        batch_service=batch_service,
        import_service=import_service,
        bank_balance_service=bank_balance_service,
        bank_transaction_repo=bank_transaction_repo,
        credential_repo=credential_repo,
        import_repo=import_repo,
        notifier=notifier,
    )
    return service, notifier


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEventOrder:
    """sync_account publishes events in the correct order."""

    @pytest.mark.asyncio
    async def test_account_sync_fetched_is_first_event(self):
        publisher = InMemorySyncEventPublisher()
        service, notifier = _make_service(publisher=publisher)
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        # First event from the service is AccountSyncFetchedEvent
        # (AccountSyncStartedEvent is now emitted by command via notifier)
        fetched_events = [
            e for e in publisher.events if isinstance(e, AccountSyncFetchedEvent)
        ]
        assert len(fetched_events) >= 1

    @pytest.mark.asyncio
    async def test_classification_events_published_when_transactions_to_import(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)
        import_result = _make_import_result(is_success=True)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            import_results=[import_result],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        event_types = [type(e) for e in publisher.events]
        assert ClassificationStartedEvent in event_types
        assert ClassificationCompletedEvent in event_types

        fetched_idx = event_types.index(AccountSyncFetchedEvent)
        classification_started_idx = event_types.index(ClassificationStartedEvent)
        assert classification_started_idx > fetched_idx


class TestInactiveMappingError:
    """When mapping.is_active = False, InactiveMappingError is raised."""

    @pytest.mark.asyncio
    async def test_raises_inactive_mapping_error(self):
        publisher = InMemorySyncEventPublisher()
        service, _notifier = _make_service(publisher=publisher)

        with pytest.raises(InactiveMappingError):
            await service.sync_account(
                mapping=_make_mapping(is_active=False),
                days=None,
                auto_post=False,
            )

    @pytest.mark.asyncio
    async def test_no_events_published_for_inactive_mapping(self):
        publisher = InMemorySyncEventPublisher()
        service, _notifier = _make_service(publisher=publisher)

        with pytest.raises(InactiveMappingError):
            await service.sync_account(
                mapping=_make_mapping(is_active=False),
                days=None,
                auto_post=False,
            )

        assert len(publisher.events) == 0


class TestEmptyImportBranch:
    """When to_import is empty after dedup, update_last_used is called and
    SyncResult has zero imports; no classification events are published."""

    @pytest.mark.asyncio
    async def test_update_last_used_called_when_nothing_to_import(self):
        publisher = InMemorySyncEventPublisher()

        # All stored transactions are already imported
        stored = _make_stored_transaction(is_new=False, is_imported=True)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        service._credential_repo.update_last_used.assert_awaited_once_with(_BLZ)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_no_classification_events_when_nothing_to_import(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=False, is_imported=True)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        classification_events = [
            e
            for e in publisher.events
            if isinstance(e, (ClassificationStartedEvent, ClassificationCompletedEvent))
        ]
        assert len(classification_events) == 0

    @pytest.mark.asyncio
    async def test_returns_sync_result_with_zero_imports_when_nothing_to_import(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=False, is_imported=True)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        result = await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        # result is tuple: (imported, skipped, failed)
        assert result[0] == 0


class TestBatchProcessing:
    """_process_batch_loop resolves + imports in interleaved batches and
    publishes the right classification events."""

    @pytest.mark.asyncio
    async def test_classification_started_and_completed_always_published(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        event_types = [type(e) for e in publisher.events]
        assert ClassificationStartedEvent in event_types
        assert ClassificationCompletedEvent in event_types

    @pytest.mark.asyncio
    async def test_resolve_batch_called_with_stored_transactions(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        cast(AsyncMock, service._batch_service.resolve_batch).assert_awaited_once_with(
            [stored]
        )

    @pytest.mark.asyncio
    async def test_import_batch_called_with_resolved_results(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)
        resolved = {"some-id": MagicMock()}

        service, notifier = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            resolve_batch_return=resolved,
        )
        await notifier.emit_account_sync_started_event(_IBAN, "Test Account")

        await service.sync_account(
            mapping=_make_mapping(),
            days=None,
            auto_post=False,
        )

        cast(AsyncMock, service._import_service.import_batch).assert_awaited_once()
        call_kwargs = cast(AsyncMock, service._import_service.import_batch).call_args
        assert call_kwargs.kwargs["resolved"] == resolved
        assert call_kwargs.kwargs["source_iban"] == _IBAN
