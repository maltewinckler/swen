"""Unit tests for BatchSyncCommand."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from swen.application.commands.integration import BatchSyncCommand
from swen.application.dtos.integration import (
    AccountCompletedEvent,
    AccountFailedEvent,
    AccountFetchedEvent,
    AccountStartedEvent,
    BatchSyncResult,
    SyncCompletedEvent,
    SyncResult,
    SyncStartedEvent,
)
from swen.domain.shared.time import today_utc, utc_now
from tests.shared.sync_streaming import collect_batch_result as _collect_batch_result

IBAN_1 = "DE89370400440532013000"
IBAN_2 = "DE91100000000123456789"


def _make_mapping(iban: str, account_name: str) -> SimpleNamespace:
    return SimpleNamespace(iban=iban, account_name=account_name)


def _make_sync_result(
    iban: str,
    start_date: date,
    end_date: date,
    imported: int,
    skipped: int = 0,
    failed: int = 0,
    fetched: int | None = None,
) -> SyncResult:
    return SyncResult(
        success=failed == 0 or imported > 0,
        synced_at=utc_now(),
        iban=iban,
        start_date=start_date,
        end_date=end_date,
        transactions_fetched=imported + skipped + failed
        if fetched is None
        else fetched,
        transactions_imported=imported,
        transactions_skipped=skipped,
        transactions_failed=failed,
    )


def _make_sync_stream(*events):
    async def stream():
        for event in events:
            yield event

    return stream()


def _make_failing_stream(error: Exception):
    async def stream():
        raise error
        yield  # pragma: no cover

    return stream()


def _make_command(opening_balance_account_exists: bool = True):
    sync_command = Mock()
    settings_repo = AsyncMock()
    settings_repo.get_or_create.return_value = SimpleNamespace(
        sync=SimpleNamespace(auto_post_transactions=True),
    )
    mapping_query = AsyncMock()
    credential_repo = AsyncMock()
    credential_repo.find_by_blz.return_value = object()

    command = BatchSyncCommand(
        sync_command=sync_command,
        settings_repo=settings_repo,
        mapping_query=mapping_query,
        credential_repo=credential_repo,
        opening_balance_account_exists=opening_balance_account_exists,
    )

    return command, sync_command, settings_repo, mapping_query, credential_repo


@pytest.mark.asyncio
async def test_execute_streaming_aggregates_account_results_and_updates_dates():
    command, sync_command, settings_repo, mapping_query, credential_repo = (
        _make_command()
    )
    mappings = [
        _make_mapping(IBAN_1, "Main Account"),
        _make_mapping(IBAN_2, "Savings Account"),
    ]
    mapping_query.execute.return_value = SimpleNamespace(mappings=mappings)
    credential_repo.find_by_blz.side_effect = [object(), object()]

    result_1 = _make_sync_result(
        iban=IBAN_1,
        start_date=date(2024, 1, 5),
        end_date=date(2024, 1, 10),
        imported=2,
        skipped=1,
    )
    result_2 = _make_sync_result(
        iban=IBAN_2,
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 12),
        imported=1,
        failed=1,
    )
    sync_command.execute_streaming.side_effect = [
        _make_sync_stream(
            AccountFetchedEvent(
                iban=IBAN_1, transactions_fetched=3, new_transactions=3
            ),
            result_1,
        ),
        _make_sync_stream(
            AccountFetchedEvent(
                iban=IBAN_2, transactions_fetched=2, new_transactions=2
            ),
            result_2,
        ),
    ]

    events = []
    async for event in command.execute_streaming(days=None, auto_post=None):
        events.append(event)

    assert isinstance(events[0], SyncStartedEvent)
    assert sum(isinstance(event, AccountStartedEvent) for event in events) == 2
    assert sum(isinstance(event, AccountCompletedEvent) for event in events) == 2
    assert isinstance(events[-2], SyncCompletedEvent)
    assert isinstance(events[-1], BatchSyncResult)

    result = events[-1]
    assert result.total_imported == 3
    assert result.total_skipped == 1
    assert result.total_failed == 1
    assert result.accounts_synced == 2
    assert result.start_date == date(2024, 1, 3)
    assert result.end_date == today_utc()

    assert settings_repo.get_or_create.await_count == 1
    assert sync_command.execute_streaming.call_args_list[0].kwargs == {
        "iban": IBAN_1,
        "auto_post": True,
    }
    assert sync_command.execute_streaming.call_args_list[1].kwargs == {
        "iban": IBAN_2,
        "auto_post": True,
    }


@pytest.mark.asyncio
async def test_execute_streaming_returns_final_result_for_fixed_date_range():
    command, sync_command, settings_repo, mapping_query, credential_repo = (
        _make_command(
            opening_balance_account_exists=False,
        )
    )
    mapping_query.execute.return_value = SimpleNamespace(
        mappings=[_make_mapping(IBAN_1, "Main Account")],
    )
    credential_repo.find_by_blz.return_value = object()

    sync_result = _make_sync_result(
        iban=IBAN_1,
        start_date=today_utc(),
        end_date=today_utc(),
        imported=4,
    )
    sync_command.execute_streaming.return_value = _make_sync_stream(sync_result)

    result = await _collect_batch_result(command, days=30)

    expected_end_date = today_utc()
    expected_start_date = expected_end_date - timedelta(days=30)

    assert result.total_imported == 4
    assert result.accounts_synced == 1
    assert result.opening_balance_account_missing is True
    assert settings_repo.get_or_create.await_count == 1
    assert sync_command.execute_streaming.call_args.kwargs == {
        "iban": IBAN_1,
        "start_date": expected_start_date,
        "end_date": expected_end_date,
        "auto_post": True,
    }


@pytest.mark.asyncio
async def test_execute_streaming_records_account_failure_and_continues():
    command, sync_command, _settings_repo, mapping_query, credential_repo = (
        _make_command()
    )
    mappings = [
        _make_mapping(IBAN_1, "Main Account"),
        _make_mapping(IBAN_2, "Savings Account"),
    ]
    mapping_query.execute.return_value = SimpleNamespace(mappings=mappings)
    credential_repo.find_by_blz.side_effect = [object(), object()]

    sync_result = _make_sync_result(
        iban=IBAN_2,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 3),
        imported=1,
    )
    sync_command.execute_streaming.side_effect = [
        _make_failing_stream(RuntimeError("bank offline")),
        _make_sync_stream(sync_result),
    ]

    events = []
    async for event in command.execute_streaming(days=7, auto_post=False):
        events.append(event)

    failure_events = [
        event for event in events if isinstance(event, AccountFailedEvent)
    ]
    assert len(failure_events) == 1
    assert failure_events[0].iban == IBAN_1
    assert failure_events[0].error == "bank offline"

    result = events[-1]
    assert isinstance(result, BatchSyncResult)
    assert result.accounts_synced == 1
    assert result.total_imported == 1
    assert result.errors == [f"{IBAN_1}: bank offline"]
