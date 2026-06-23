"""Unit tests for SyncNotificationService.

Covers:
- Each emit method publishes the correct event type with correct fields
- Internal state accumulation (totals, account_index auto-increment)
- Success computation in emit_sync_result_event
- close() delegates to publisher
"""

from __future__ import annotations

import pytest

from swen.application.events import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    BatchSyncCompletedEvent,
    BatchSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
    ErrorCode,
    SyncResultEvent,
)
from swen.application.integration.services.sync_notification_service import (
    SyncNotificationService,
)
from tests.shared.sync_event_publisher import InMemorySyncEventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_notifier() -> tuple[SyncNotificationService, InMemorySyncEventPublisher]:
    publisher = InMemorySyncEventPublisher()
    return SyncNotificationService(publisher), publisher


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBatchLifecycle:
    """Batch-level events: started, completed, result."""

    @pytest.mark.asyncio
    async def test_emit_batch_sync_started_event(self):
        notifier, publisher = _make_notifier()

        await notifier.emit_batch_sync_started_event(3)

        assert len(publisher.events) == 1
        event = publisher.events[0]
        assert isinstance(event, BatchSyncStartedEvent)
        assert event.total_accounts == 3

    @pytest.mark.asyncio
    async def test_emit_batch_sync_completed_event_reads_internal_totals(self):
        notifier, publisher = _make_notifier()

        # Simulate some account completions to accumulate totals
        await notifier.emit_batch_sync_started_event(2)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_completed_event(5, 2, 1)
        await notifier.emit_account_sync_started_event("DE2222", "Account 2")
        await notifier.emit_account_sync_completed_event(3, 0, 0)

        await notifier.emit_batch_sync_completed_event()

        completed = publisher.events[-1]
        assert isinstance(completed, BatchSyncCompletedEvent)
        assert completed.total_imported == 8
        assert completed.total_skipped == 2
        assert completed.total_failed == 1
        assert completed.accounts_synced == 2

    @pytest.mark.asyncio
    async def test_emit_sync_result_event_success_when_no_failures(self):
        notifier, publisher = _make_notifier()

        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_completed_event(5, 0, 0)

        await notifier.emit_sync_result_event()

        result = publisher.events[-1]
        assert isinstance(result, SyncResultEvent)
        assert result.success is True
        assert result.total_imported == 5

    @pytest.mark.asyncio
    async def test_emit_sync_result_event_success_when_failures_but_some_imported(self):
        notifier, publisher = _make_notifier()

        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_completed_event(3, 0, 2)

        await notifier.emit_sync_result_event()

        result = publisher.events[-1]
        assert isinstance(result, SyncResultEvent)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_emit_sync_result_event_failure_when_only_failures(self):
        notifier, publisher = _make_notifier()

        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_completed_event(0, 0, 3)

        await notifier.emit_sync_result_event()

        result = publisher.events[-1]
        assert isinstance(result, SyncResultEvent)
        assert result.success is False


class TestAccountLifecycle:
    """Account-level events: started, completed, failed."""

    @pytest.mark.asyncio
    async def test_emit_account_sync_started_auto_increments_index(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(3)

        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_started_event("DE2222", "Account 2")
        await notifier.emit_account_sync_started_event("DE3333", "Account 3")

        started_events = [
            e for e in publisher.events if isinstance(e, AccountSyncStartedEvent)
        ]
        assert len(started_events) == 3
        assert started_events[0].account_index == 1
        assert started_events[1].account_index == 2
        assert started_events[2].account_index == 3

        # All carry total_accounts
        for e in started_events:
            assert e.total_accounts == 3

    @pytest.mark.asyncio
    async def test_emit_account_sync_started_sets_iban_context(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)

        await notifier.emit_account_sync_started_event("DE1111", "My Account")

        event = publisher.events[-1]
        assert isinstance(event, AccountSyncStartedEvent)
        assert event.iban == "DE1111"
        assert event.account_name == "My Account"

    @pytest.mark.asyncio
    async def test_emit_account_sync_completed_accumulates_totals(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(2)

        await notifier.emit_account_sync_started_event("DE1111", "Account 1")
        await notifier.emit_account_sync_completed_event(10, 3, 1)

        event = publisher.events[-1]
        assert isinstance(event, AccountSyncCompletedEvent)
        assert event.iban == "DE1111"
        assert event.imported == 10
        assert event.skipped == 3
        assert event.failed == 1

    @pytest.mark.asyncio
    async def test_emit_account_sync_failed_uses_iban_from_state(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")

        await notifier.emit_account_sync_failed_event(
            code=ErrorCode.BANK_CONNECTION_ERROR,
            error_key="connection refused",
        )

        event = publisher.events[-1]
        assert isinstance(event, AccountSyncFailedEvent)
        assert event.iban == "DE1111"
        assert event.code == ErrorCode.BANK_CONNECTION_ERROR
        assert event.error_key == "connection refused"


class TestAccountDetails:
    """Account-detail events: fetched."""

    @pytest.mark.asyncio
    async def test_emit_account_sync_fetched_uses_iban_from_state(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")

        await notifier.emit_account_sync_fetched_event(
            transactions_fetched=42, new_transactions=7
        )

        event = publisher.events[-1]
        assert isinstance(event, AccountSyncFetchedEvent)
        assert event.iban == "DE1111"
        assert event.transactions_fetched == 42
        assert event.new_transactions == 7


class TestClassificationEvents:
    """Classification events: started, progress, classified, completed."""

    @pytest.mark.asyncio
    async def test_emit_classification_started(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")

        await notifier.emit_classification_started_event()

        event = publisher.events[-1]
        assert isinstance(event, ClassificationStartedEvent)
        assert event.iban == "DE1111"

    @pytest.mark.asyncio
    async def test_emit_classification_progress(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")

        await notifier.emit_classification_progress_event(current=3, total=10)

        event = publisher.events[-1]
        assert isinstance(event, ClassificationProgressEvent)
        assert event.iban == "DE1111"
        assert event.current == 3
        assert event.total == 10

    @pytest.mark.asyncio
    async def test_emit_classification_completed(self):
        notifier, publisher = _make_notifier()
        await notifier.emit_batch_sync_started_event(1)
        await notifier.emit_account_sync_started_event("DE1111", "Account 1")

        await notifier.emit_classification_completed_event(
            total=10, processing_time_ms=1500
        )

        event = publisher.events[-1]
        assert isinstance(event, ClassificationCompletedEvent)
        assert event.iban == "DE1111"
        assert event.total == 10
        assert event.processing_time_ms == 1500


class TestClose:
    """close() delegates to publisher."""

    @pytest.mark.asyncio
    async def test_close_delegates_to_publisher(self):
        notifier, publisher = _make_notifier()

        await notifier.close()

        assert publisher.closed is True
