"""Unit tests for BankAccountSyncService.

Covers:
- Event order: AccountSyncStartedEvent → AccountSyncFetchedEvent → classification
  events → TransactionClassifiedEvent per success
- InactiveMappingError when mapping.is_active = False
- Empty-import branch: update_last_used called, SyncResult with zero imports,
  no classification events
- ML publish-through: _classify_to_publisher drains the ML stream and publishes
  classification events
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import AsyncIterator, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.dtos.integration import (
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationStartedEvent,
    SyncPeriod,
    SyncResult,
    TransactionClassifiedEvent,
)
from swen.application.services.integration.bank_account_sync_service import (
    BankAccountSyncService,
)
from swen.application.services.integration.exceptions import InactiveMappingError
from swen.domain.accounting.services.opening_balance.service import (
    OpeningBalanceOutcome,
)
from swen.domain.integration.entities import AccountMapping
from tests.shared.sync_event_publisher import InMemorySyncEventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2024, 1, 15)
_SYNCED_AT = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
_IBAN = "DE89370400440532013000"
_BLZ = "37040044"


def _make_mapping(*, is_active: bool = True) -> AccountMapping:
    return cast(
        "AccountMapping",
        SimpleNamespace(iban=_IBAN, account_name="Test Account", is_active=is_active),
    )


def _make_period() -> SyncPeriod:
    return SyncPeriod(start_date=_TODAY, end_date=_TODAY, adaptive=False)


def _make_sync_result() -> SyncResult:
    return SyncResult(
        success=True,
        synced_at=_SYNCED_AT,
        iban=_IBAN,
        start_date=_TODAY,
        end_date=_TODAY,
        transactions_fetched=2,
        transactions_imported=1,
        transactions_skipped=1,
        transactions_failed=0,
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


async def _empty_async_gen():
    """Async generator that yields nothing."""
    return
    yield  # make it an async generator


async def _classification_events_gen(iban: str):
    """Async generator that yields classification events then a result dict."""
    yield ClassificationStartedEvent(iban=iban)
    yield ClassificationCompletedEvent(iban=iban, total=1)
    yield {}  # preclassified dict


async def _import_streaming_gen(results):
    """Async generator that yields (index, total, result) tuples."""
    total = len(results)
    for i, result in enumerate(results, start=1):
        yield i, total, result


def _make_service(
    *,
    publisher: InMemorySyncEventPublisher,
    bank_transactions=None,
    stored_transactions=None,
    classification_gen=None,
    import_results=None,
    sync_result: SyncResult | None = None,
) -> BankAccountSyncService:
    """Build a BankAccountSyncService with all dependencies mocked."""
    if bank_transactions is None:
        bank_transactions = []
    if stored_transactions is None:
        stored_transactions = []
    if import_results is None:
        import_results = []
    if sync_result is None:
        sync_result = _make_sync_result()

    bank_fetch_service = AsyncMock()
    bank_fetch_service.fetch_transactions.return_value = bank_transactions

    bank_transaction_repo = AsyncMock()
    bank_transaction_repo.save_batch_with_deduplication.return_value = (
        stored_transactions
    )

    current_balance_service = AsyncMock()
    current_balance_service.for_iban.return_value = None

    opening_balance_service = AsyncMock()
    opening_balance_service.try_create_for_first_sync.return_value = (
        OpeningBalanceOutcome(created=False)
    )

    ml_classification_service = AsyncMock()
    if classification_gen is not None:
        ml_classification_service.classify_batch_streaming = classification_gen
    else:

        async def _default_classification_gen(*args, **kwargs):
            return
            yield  # make it an async generator

        ml_classification_service.classify_batch_streaming = _default_classification_gen

    import_service = AsyncMock()
    _results = import_results

    async def _import_streaming(*args, **kwargs) -> AsyncIterator:
        async for item in _import_streaming_gen(_results):
            yield item

    import_service.import_streaming = _import_streaming

    result_aggregator = MagicMock()
    result_aggregator.build.return_value = sync_result

    period_resolver = AsyncMock()
    period_resolver.resolve_adaptive_for.return_value = _make_period()

    credential_repo = AsyncMock()
    credential_repo.get_tan_settings.return_value = (None, None)
    credential_repo.update_last_used = AsyncMock()

    import_repo = AsyncMock()

    return BankAccountSyncService(
        bank_fetch_service=bank_fetch_service,
        opening_balance_service=opening_balance_service,
        ml_classification_service=ml_classification_service,
        import_service=import_service,
        result_aggregator=result_aggregator,
        period_resolver=period_resolver,
        current_balance_service=current_balance_service,
        bank_transaction_repo=bank_transaction_repo,
        import_repo=import_repo,
        credential_repo=credential_repo,
        publisher=publisher,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEventOrder:
    """sync_account publishes events in the correct order."""

    @pytest.mark.asyncio
    async def test_account_sync_started_is_first_event(self):
        publisher = InMemorySyncEventPublisher()
        service = _make_service(publisher=publisher)

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        assert len(publisher.events) >= 1
        assert isinstance(publisher.events[0], AccountSyncStartedEvent)

    @pytest.mark.asyncio
    async def test_account_sync_fetched_follows_started(self):
        publisher = InMemorySyncEventPublisher()
        service = _make_service(publisher=publisher)

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        event_types = [type(e) for e in publisher.events]
        started_idx = event_types.index(AccountSyncStartedEvent)
        fetched_idx = event_types.index(AccountSyncFetchedEvent)
        assert fetched_idx > started_idx

    @pytest.mark.asyncio
    async def test_classification_events_published_between_fetched_and_classified(self):
        publisher = InMemorySyncEventPublisher()

        # One stored transaction that needs importing
        stored = _make_stored_transaction(is_new=True, is_imported=False)
        import_result = _make_import_result(is_success=True)

        async def _classification_gen(*args, **kwargs):
            yield ClassificationStartedEvent(iban=_IBAN)
            yield ClassificationCompletedEvent(iban=_IBAN, total=1)
            yield {}

        ml_service = AsyncMock()
        ml_service.classify_batch_streaming = _classification_gen

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            import_results=[import_result],
        )
        # Override the ML service
        service._ml_classification_service = ml_service

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        event_types = [type(e) for e in publisher.events]
        assert ClassificationStartedEvent in event_types
        assert ClassificationCompletedEvent in event_types

        fetched_idx = event_types.index(AccountSyncFetchedEvent)
        classification_started_idx = event_types.index(ClassificationStartedEvent)
        assert classification_started_idx > fetched_idx

    @pytest.mark.asyncio
    async def test_transaction_classified_published_per_success(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)
        import_result = _make_import_result(is_success=True)

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            import_results=[import_result],
        )

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        classified_events = [
            e for e in publisher.events if isinstance(e, TransactionClassifiedEvent)
        ]
        assert len(classified_events) == 1

    @pytest.mark.asyncio
    async def test_failed_import_does_not_publish_classified_event(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)
        import_result = _make_import_result(is_success=False)

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            import_results=[import_result],
        )

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        classified_events = [
            e for e in publisher.events if isinstance(e, TransactionClassifiedEvent)
        ]
        assert len(classified_events) == 0


class TestInactiveMappingError:
    """When mapping.is_active = False, InactiveMappingError is raised."""

    @pytest.mark.asyncio
    async def test_raises_inactive_mapping_error(self):
        publisher = InMemorySyncEventPublisher()
        service = _make_service(publisher=publisher)

        with pytest.raises(InactiveMappingError):
            await service.sync_account(
                mapping=_make_mapping(is_active=False),
                credentials=MagicMock(),
                period=_make_period(),
                auto_post=False,
                account_index=1,
                total_accounts=1,
            )

    @pytest.mark.asyncio
    async def test_no_events_published_for_inactive_mapping(self):
        publisher = InMemorySyncEventPublisher()
        service = _make_service(publisher=publisher)

        with pytest.raises(InactiveMappingError):
            await service.sync_account(
                mapping=_make_mapping(is_active=False),
                credentials=MagicMock(),
                period=_make_period(),
                auto_post=False,
                account_index=1,
                total_accounts=1,
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

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        service._credential_repo.update_last_used.assert_awaited_once_with(_BLZ)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_no_classification_events_when_nothing_to_import(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=False, is_imported=True)

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
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
        zero_import_result = SyncResult(
            success=True,
            synced_at=_SYNCED_AT,
            iban=_IBAN,
            start_date=_TODAY,
            end_date=_TODAY,
            transactions_fetched=1,
            transactions_imported=0,
            transactions_skipped=1,
            transactions_failed=0,
        )

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
            sync_result=zero_import_result,
        )

        result = await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        assert result.transactions_imported == 0


class TestMLPublishThrough:
    """_classify_to_publisher drains the ML stream and publishes classification
    events to the publisher."""

    @pytest.mark.asyncio
    async def test_classification_events_published_from_ml_stream(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)

        async def _classification_gen(*args, **kwargs):
            yield ClassificationStartedEvent(iban=_IBAN)
            yield ClassificationCompletedEvent(iban=_IBAN, total=1)
            yield {}  # preclassified dict

        ml_service = AsyncMock()
        ml_service.classify_batch_streaming = _classification_gen

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        service._ml_classification_service = ml_service

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        event_types = [type(e) for e in publisher.events]
        assert ClassificationStartedEvent in event_types
        assert ClassificationCompletedEvent in event_types

    @pytest.mark.asyncio
    async def test_dict_items_from_ml_stream_not_published_as_events(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)

        async def _classification_gen(*args, **kwargs):
            yield ClassificationStartedEvent(iban=_IBAN)
            yield {"some-uuid": MagicMock()}  # preclassified dict — not an event

        ml_service = AsyncMock()
        ml_service.classify_batch_streaming = _classification_gen

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        service._ml_classification_service = ml_service

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        # Only ClassificationStartedEvent should be in events, not the dict
        for event in publisher.events:
            assert not isinstance(event, dict)

    @pytest.mark.asyncio
    async def test_empty_ml_stream_publishes_no_classification_events(self):
        publisher = InMemorySyncEventPublisher()

        stored = _make_stored_transaction(is_new=True, is_imported=False)

        async def _empty_classification_gen(*args, **kwargs):
            return
            yield  # make it an async generator

        ml_service = AsyncMock()
        ml_service.classify_batch_streaming = _empty_classification_gen

        service = _make_service(
            publisher=publisher,
            bank_transactions=[MagicMock()],
            stored_transactions=[stored],
        )
        service._ml_classification_service = ml_service

        await service.sync_account(
            mapping=_make_mapping(),
            credentials=MagicMock(),
            period=_make_period(),
            auto_post=False,
            account_index=1,
            total_accounts=1,
        )

        classification_events = [
            e
            for e in publisher.events
            if isinstance(e, (ClassificationStartedEvent, ClassificationCompletedEvent))
        ]
        assert len(classification_events) == 0
