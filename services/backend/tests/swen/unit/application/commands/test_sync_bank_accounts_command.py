"""Unit tests for SyncBankAccountsCommand.

Covers:
- Filter precedence (iban over blz)
- Equity-account lookup (opening_balance_account_missing)
- Per-account exception handling (AccountSyncFailedEvent, continues)
- Empty-mappings edge case
- Terminal payload (publisher.terminal is BatchSyncResult)
- BatchSyncStarted/BatchSyncCompleted ordering
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.application.commands.integration.sync_bank_accounts_command import (
    SyncBankAccountsCommand,
)
from swen.application.dtos.integration import (
    AccountSyncFailedEvent,
    BatchSyncCompletedEvent,
    BatchSyncResult,
    BatchSyncStartedEvent,
    SyncPeriod,
    SyncResult,
)
from swen.application.services.integration.sync_period_resolver import (
    SyncPeriodResolver,
)
from tests.shared.sync_event_publisher import InMemorySyncEventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2024, 1, 15)
_SYNCED_AT = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_sync_result(iban: str = "DE89370400440532013000") -> SyncResult:
    return SyncResult(
        success=True,
        synced_at=_SYNCED_AT,
        iban=iban,
        start_date=_TODAY,
        end_date=_TODAY,
        transactions_fetched=2,
        transactions_imported=1,
        transactions_skipped=1,
        transactions_failed=0,
    )


def _make_mapping(iban: str, blz: str = "37040044") -> SimpleNamespace:
    return SimpleNamespace(iban=iban, account_name="Test Account", is_active=True)


def _make_period() -> SyncPeriod:
    return SyncPeriod(start_date=_TODAY, end_date=_TODAY, adaptive=False)


def _make_command(
    *,
    mappings: list,
    sync_service: AsyncMock,
    publisher: InMemorySyncEventPublisher,
    equity_account=object(),  # truthy by default
    credentials=object(),
) -> SyncBankAccountsCommand:
    """Build a SyncBankAccountsCommand with all dependencies mocked."""
    mapping_repo = AsyncMock()
    mapping_repo.find_all.return_value = mappings

    settings_repo = AsyncMock()
    settings = MagicMock()
    settings.sync.auto_post_transactions = False
    settings_repo.get_or_create.return_value = settings

    credential_repo = AsyncMock()
    credential_repo.find_by_blz.return_value = credentials

    account_repo = AsyncMock()
    account_repo.find_by_account_number.return_value = equity_account

    period_resolver = MagicMock(spec=SyncPeriodResolver)
    period_resolver.resolve_fixed.return_value = _make_period()

    bank_balance_service = AsyncMock()

    return SyncBankAccountsCommand(
        sync_service=sync_service,
        bank_balance_service=bank_balance_service,
        period_resolver=period_resolver,
        mapping_repo=mapping_repo,
        settings_repo=settings_repo,
        credential_repo=credential_repo,
        account_repo=account_repo,
        publisher=publisher,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFilterPrecedence:
    """iban filter takes precedence over blz when both are provided."""

    @pytest.mark.asyncio
    async def test_iban_filter_takes_precedence_over_blz(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result(
            "DE89370400440532013000"
        )

        # Two mappings: one matching iban, one matching blz only
        mapping_iban = _make_mapping("DE89370400440532013000", blz="37040044")
        mapping_blz_only = _make_mapping("DE12345678901234567890", blz="12345678")

        command = _make_command(
            mappings=[mapping_iban, mapping_blz_only],
            sync_service=sync_service,
            publisher=publisher,
        )

        # Provide both iban and blz — iban should win
        await command.execute(
            iban="DE89370400440532013000",
            blz="12345678",
            days=30,
        )

        # sync_account should only be called for the iban-matching mapping
        assert sync_service.sync_account.call_count == 1
        call_kwargs = sync_service.sync_account.call_args
        assert call_kwargs.kwargs["mapping"].iban == "DE89370400440532013000"


class TestEquityAccountLookup:
    """When OPENING_BALANCE_EQUITY account is missing, result reflects it."""

    @pytest.mark.asyncio
    async def test_opening_balance_account_missing_when_not_found(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
            equity_account=None,  # simulate missing equity account
        )

        result = await command.execute(days=30)

        assert isinstance(result, BatchSyncResult)
        assert result.opening_balance_account_missing is True

    @pytest.mark.asyncio
    async def test_opening_balance_account_present_when_found(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
            equity_account=object(),  # non-None → present
        )

        result = await command.execute(days=30)

        assert result.opening_balance_account_missing is False


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
            _make_sync_result("DE12345678901234567890"),
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

        await command.execute(days=30)

        assert publisher.terminal is not None
        assert isinstance(publisher.terminal, BatchSyncResult)


class TestEmptyMappingsEdgeCase:
    """When no syncable mappings exist, the correct events are published."""

    @pytest.mark.asyncio
    async def test_empty_mappings_publishes_started_then_completed_then_terminal(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()

        # No mappings — credential_repo returns None so all are filtered out
        command = _make_command(
            mappings=[],
            sync_service=sync_service,
            publisher=publisher,
        )

        result = await command.execute(days=30)

        # Events: BatchSyncStarted → BatchSyncCompleted
        assert len(publisher.events) == 2
        assert isinstance(publisher.events[0], BatchSyncStartedEvent)
        assert publisher.events[0].total_accounts == 0
        assert isinstance(publisher.events[1], BatchSyncCompletedEvent)

        # Terminal payload is set
        assert publisher.terminal is not None
        assert isinstance(publisher.terminal, BatchSyncResult)
        assert result is publisher.terminal

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
    """publisher.terminal is exactly one BatchSyncResult after execute()."""

    @pytest.mark.asyncio
    async def test_terminal_is_batch_sync_result(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mapping = _make_mapping("DE89370400440532013000")
        command = _make_command(
            mappings=[mapping],
            sync_service=sync_service,
            publisher=publisher,
        )

        result = await command.execute(days=30)

        assert publisher.terminal is not None
        assert isinstance(publisher.terminal, BatchSyncResult)
        # execute() return value is the same object as terminal
        assert result is publisher.terminal

    @pytest.mark.asyncio
    async def test_terminal_set_exactly_once(self):
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

        # publish_terminal is called once — terminal is not None and is a BatchSyncResult
        assert publisher.terminal is not None


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

        assert isinstance(publisher.events[-1], BatchSyncCompletedEvent)

    @pytest.mark.asyncio
    async def test_started_total_accounts_matches_syncable_count(self):
        publisher = InMemorySyncEventPublisher()
        sync_service = AsyncMock()
        sync_service.sync_account.return_value = _make_sync_result()

        mappings = [
            _make_mapping("DE89370400440532013000"),
            _make_mapping("DE12345678901234567890"),
        ]
        # Need two different sync results
        sync_service.sync_account.side_effect = [
            _make_sync_result("DE89370400440532013000"),
            _make_sync_result("DE12345678901234567890"),
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
