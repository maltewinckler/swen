"""Unit tests for SyncBankAccountsCommand.

Covers:
- Per-account exception handling (AccountSyncFailedEvent, continues)
- Empty-mappings edge case
- Terminal payload (SyncResultEvent published; publisher.closed is True)
- BatchSyncStarted/BatchSyncCompleted ordering
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.commands.integration.sync_bank_accounts_command import (
    SyncBankAccountsCommand,
)
from swen.application.events import (
    AccountSyncFailedEvent,
    BatchSyncCompletedEvent,
    BatchSyncStartedEvent,
    SyncResultEvent,
)
from swen.application.services.integration.sync_notification_service import (
    SyncNotificationService,
)
from swen.domain.integration.value_objects.sync_period import SyncPeriod
from tests.shared.sync_event_publisher import InMemorySyncEventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2024, 1, 15)


def _make_sync_result() -> tuple[int, int, int]:
    """Return a sync result tuple: (imported, skipped, failed)."""
    return (1, 1, 0)


def _make_mapping(iban: str, blz: str = "37040044") -> SimpleNamespace:
    return SimpleNamespace(iban=iban, account_name="Test Account", is_active=True)


def _make_period() -> SyncPeriod:
    return SyncPeriod(start_date=_TODAY, end_date=_TODAY, adaptive=False)


def _make_command(
    *,
    mappings: list,
    sync_service: AsyncMock,
    publisher: InMemorySyncEventPublisher,
) -> SyncBankAccountsCommand:
    """Build a SyncBankAccountsCommand with all dependencies mocked."""
    mapping_repo = AsyncMock()
    mapping_repo.find_all.return_value = mappings

    settings_repo = AsyncMock()
    settings = MagicMock()
    settings.sync.auto_post_transactions = False
    settings_repo.get_or_create.return_value = settings

    notifier = SyncNotificationService(publisher)

    return SyncBankAccountsCommand(
        sync_service=sync_service,
        mapping_repo=mapping_repo,
        settings_repo=settings_repo,
        notifier=notifier,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPerAccountExceptionHandling:
    """When sync_service.sync_account raises, one AccountSyncFailedEvent is
    published and the next mapping is still processed."""

    @pytest.mark.asyncio
    async def test_exception_publishes_failed_event_and_continues(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()

        mapping_fail = _make_mapping("DE89370400440532013000")
        mapping_ok = _make_mapping("DE12345678901234567890")

        # First call raises, second succeeds
        sync_service.sync_account.side_effect = [
            RuntimeError("bank error"),
            _make_sync_result(),
        ]

        command = _make_command(
            mappings=[mapping_fail, mapping_ok],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        failed_events = [
            e for e in publisher.events if isinstance(e, AccountSyncFailedEvent)
        ]
        assert len(failed_events) == 1
        assert failed_events[0].iban == "DE89370400440532013000"

        # Second mapping was still processed
        assert sync_service.sync_account.call_count == 2

    @pytest.mark.asyncio
    async def test_exception_does_not_prevent_terminal_payload(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.side_effect = RuntimeError("bank error")

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        result = await command.execute(days=30)

        assert result is None
        assert publisher.closed is True


class TestEmptyMappingsEdgeCase:
    """When no syncable mappings exist, the correct events are published."""

    @pytest.mark.asyncio
    async def test_empty_mappings_publishes_started_then_completed_then_terminal(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()

        command = _make_command(
            mappings=[],
            sync_service=sync_service,
            publisher=publisher,
        )

        result = await command.execute(days=30)

        # Events: BatchSyncStarted → BatchSyncCompleted → SyncResultEvent
        assert len(publisher.events) == 3
        assert isinstance(publisher.events[0], BatchSyncStartedEvent)
        assert publisher.events[0].total_accounts == 0
        assert isinstance(publisher.events[1], BatchSyncCompletedEvent)
        assert isinstance(publisher.events[2], SyncResultEvent)

        # execute() returns None; publisher is closed
        assert result is None
        assert publisher.closed is True

    @pytest.mark.asyncio
    async def test_empty_mappings_completed_event_has_zero_counts(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()

        command = _make_command(
            mappings=[],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        completed = publisher.events[1]
        assert isinstance(completed, BatchSyncCompletedEvent)
        assert completed.total_imported == 0
        assert completed.total_skipped == 0
        assert completed.total_failed == 0
        assert completed.accounts_synced == 0


class TestTerminalPayload:
    """SyncResultEvent is published and the publisher is closed."""

    @pytest.mark.asyncio
    async def test_execute_publishes_sync_result_event(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        assert any(isinstance(e, SyncResultEvent) for e in publisher.events)

    @pytest.mark.asyncio
    async def test_publisher_closed_after_execute(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        assert publisher.closed is True


class TestBatchSyncStartedCompletedOrdering:
    """First event is BatchSyncStartedEvent; last progress event before
    terminal is BatchSyncCompletedEvent."""

    @pytest.mark.asyncio
    async def test_first_event_is_batch_sync_started(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        assert isinstance(publisher.events[0], BatchSyncStartedEvent)

    @pytest.mark.asyncio
    async def test_last_event_is_batch_sync_completed(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        # SyncResultEvent is the last published event; BatchSyncCompleted is second-to-last
        assert isinstance(publisher.events[-1], SyncResultEvent)
        assert isinstance(publisher.events[-2], BatchSyncCompletedEvent)

    @pytest.mark.asyncio
    async def test_started_total_accounts_matches_syncable_count(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()

        mappings = [
            _make_mapping("DE89370400440532013000"),
            _make_mapping("DE12345678901234567890"),
        ]
        # Need two different sync results
        sync_service.sync_account.side_effect = [
            _make_sync_result(),
            _make_sync_result(),
        ]

        command = _make_command(
            mappings=mappings,
            sync_service=sync_service,
            publisher=publisher,
        )

        await command.execute(days=30)

        started = publisher.events[0]
        assert isinstance(started, BatchSyncStartedEvent)
        assert started.total_accounts == 2
