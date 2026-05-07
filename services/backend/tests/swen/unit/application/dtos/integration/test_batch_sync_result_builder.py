"""Unit tests for BatchSyncResultBuilder and BatchSyncResult.

Covers:
- add_account: aggregates totals and per-account stats
- add_error: records per-account errors in "<iban>: <error>" format
- widen_period: expands start/end dates
- build: produces a frozen BatchSyncResult with tuple fields
- FrozenInstanceError raised when attempting to mutate any field on the built result
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from swen.application.dtos.integration.batch_sync_result import (
    BatchSyncResult,
    BatchSyncResultBuilder,
)
from swen.application.dtos.integration.sync_result import SyncResult

_SYNCED_AT = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
_START = date(2024, 6, 1)
_END = date(2024, 6, 15)
_IBAN_A = "DE89370400440532013000"
_IBAN_B = "DE12500000001234567890"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_builder(
    *,
    start_date: date = _START,
    end_date: date = _END,
    auto_post: bool = False,
    opening_balance_account_missing: bool = False,
) -> BatchSyncResultBuilder:
    return BatchSyncResultBuilder(
        synced_at=_SYNCED_AT,
        start_date=start_date,
        end_date=end_date,
        auto_post=auto_post,
        opening_balance_account_missing=opening_balance_account_missing,
    )


def _make_sync_result(
    iban: str = _IBAN_A,
    *,
    fetched: int = 5,
    imported: int = 3,
    skipped: int = 1,
    failed: int = 1,
    reconciled: int = 0,
    error_message: str | None = None,
    opening_balance_created: bool = False,
    opening_balance_amount: Decimal | None = None,
) -> SyncResult:
    return SyncResult(
        success=failed == 0 or imported > 0,
        synced_at=_SYNCED_AT,
        iban=iban,
        start_date=_START,
        end_date=_END,
        transactions_fetched=fetched,
        transactions_imported=imported,
        transactions_skipped=skipped,
        transactions_failed=failed,
        transactions_reconciled=reconciled,
        error_message=error_message,
        opening_balance_created=opening_balance_created,
        opening_balance_amount=opening_balance_amount,
    )


# ---------------------------------------------------------------------------
# add_account
# ---------------------------------------------------------------------------


class TestAddAccount:
    """add_account aggregates totals and appends per-account stats."""

    def test_totals_accumulated_from_single_account(self):
        builder = _make_builder()
        builder.add_account(
            _make_sync_result(fetched=5, imported=3, skipped=1, failed=1)
        )
        result = builder.build()

        assert result.total_fetched == 5
        assert result.total_imported == 3
        assert result.total_skipped == 1
        assert result.total_failed == 1

    def test_totals_accumulated_from_multiple_accounts(self):
        builder = _make_builder()
        builder.add_account(
            _make_sync_result(_IBAN_A, fetched=5, imported=3, skipped=1, failed=1)
        )
        builder.add_account(
            _make_sync_result(_IBAN_B, fetched=4, imported=2, skipped=2, failed=0)
        )
        result = builder.build()

        assert result.total_fetched == 9
        assert result.total_imported == 5
        assert result.total_skipped == 3
        assert result.total_failed == 1

    def test_account_stats_tuple_has_one_entry_per_add_account(self):
        builder = _make_builder()
        builder.add_account(_make_sync_result(_IBAN_A))
        builder.add_account(_make_sync_result(_IBAN_B))
        result = builder.build()

        assert len(result.account_stats) == 2

    def test_account_stats_iban_matches(self):
        builder = _make_builder()
        builder.add_account(_make_sync_result(_IBAN_A))
        result = builder.build()

        assert result.account_stats[0].iban == _IBAN_A

    def test_error_message_from_sync_result_added_to_errors(self):
        builder = _make_builder()
        builder.add_account(
            _make_sync_result(_IBAN_A, error_message="something went wrong")
        )
        result = builder.build()

        assert len(result.errors) == 1
        assert _IBAN_A in result.errors[0]
        assert "something went wrong" in result.errors[0]

    def test_no_error_added_when_sync_result_has_no_error_message(self):
        builder = _make_builder()
        builder.add_account(_make_sync_result(_IBAN_A, error_message=None))
        result = builder.build()

        assert len(result.errors) == 0

    def test_opening_balance_added_when_created(self):
        builder = _make_builder()
        builder.add_account(
            _make_sync_result(
                _IBAN_A,
                opening_balance_created=True,
                opening_balance_amount=Decimal("800.00"),
            )
        )
        result = builder.build()

        assert len(result.opening_balances) == 1
        assert result.opening_balances[0].iban == _IBAN_A
        assert result.opening_balances[0].amount == Decimal("800.00")

    def test_no_opening_balance_added_when_not_created(self):
        builder = _make_builder()
        builder.add_account(_make_sync_result(_IBAN_A, opening_balance_created=False))
        result = builder.build()

        assert len(result.opening_balances) == 0


# ---------------------------------------------------------------------------
# add_error
# ---------------------------------------------------------------------------


class TestAddError:
    """add_error records per-account errors in '<iban>: <error>' format."""

    def test_error_format_is_iban_colon_error(self):
        builder = _make_builder()
        builder.add_error(_IBAN_A, "connection timeout")
        result = builder.build()

        assert result.errors == (f"{_IBAN_A}: connection timeout",)

    def test_multiple_errors_accumulated(self):
        builder = _make_builder()
        builder.add_error(_IBAN_A, "error A")
        builder.add_error(_IBAN_B, "error B")
        result = builder.build()

        assert len(result.errors) == 2

    def test_errors_from_add_error_and_add_account_combined(self):
        builder = _make_builder()
        builder.add_error(_IBAN_A, "direct error")
        builder.add_account(_make_sync_result(_IBAN_B, error_message="account error"))
        result = builder.build()

        assert len(result.errors) == 2


# ---------------------------------------------------------------------------
# widen_period
# ---------------------------------------------------------------------------


class TestWidenPeriod:
    """widen_period expands the date window."""

    def test_widen_extends_start_date_earlier(self):
        builder = _make_builder(start_date=date(2024, 6, 1))
        builder.widen_period(date(2024, 5, 15), date(2024, 6, 15))
        result = builder.build()

        assert result.start_date == date(2024, 5, 15)

    def test_widen_extends_end_date_later(self):
        builder = _make_builder(end_date=date(2024, 6, 15))
        builder.widen_period(date(2024, 6, 1), date(2024, 6, 30))
        result = builder.build()

        assert result.end_date == date(2024, 6, 30)

    def test_widen_does_not_shrink_start_date(self):
        builder = _make_builder(start_date=date(2024, 6, 1))
        builder.widen_period(date(2024, 6, 5), date(2024, 6, 15))
        result = builder.build()

        # start_date should remain 2024-06-01 (not widened to later date)
        assert result.start_date == date(2024, 6, 1)

    def test_widen_does_not_shrink_end_date(self):
        builder = _make_builder(end_date=date(2024, 6, 30))
        builder.widen_period(date(2024, 6, 1), date(2024, 6, 15))
        result = builder.build()

        assert result.end_date == date(2024, 6, 30)

    def test_multiple_widen_calls_accumulate(self):
        builder = _make_builder(start_date=date(2024, 6, 1), end_date=date(2024, 6, 15))
        builder.widen_period(date(2024, 5, 20), date(2024, 6, 20))
        builder.widen_period(date(2024, 5, 10), date(2024, 6, 25))
        result = builder.build()

        assert result.start_date == date(2024, 5, 10)
        assert result.end_date == date(2024, 6, 25)


# ---------------------------------------------------------------------------
# build — frozen result with tuple fields
# ---------------------------------------------------------------------------


class TestBuild:
    """build() returns a frozen BatchSyncResult with tuple-typed collections."""

    def test_build_returns_batch_sync_result(self):
        builder = _make_builder()
        result = builder.build()

        assert isinstance(result, BatchSyncResult)

    def test_account_stats_is_tuple(self):
        builder = _make_builder()
        builder.add_account(_make_sync_result())
        result = builder.build()

        assert isinstance(result.account_stats, tuple)

    def test_opening_balances_is_tuple(self):
        builder = _make_builder()
        result = builder.build()

        assert isinstance(result.opening_balances, tuple)

    def test_errors_is_tuple(self):
        builder = _make_builder()
        result = builder.build()

        assert isinstance(result.errors, tuple)

    def test_empty_build_has_zero_totals(self):
        builder = _make_builder()
        result = builder.build()

        assert result.total_fetched == 0
        assert result.total_imported == 0
        assert result.total_skipped == 0
        assert result.total_failed == 0

    def test_auto_post_preserved(self):
        builder = _make_builder(auto_post=True)
        result = builder.build()

        assert result.auto_post is True

    def test_opening_balance_account_missing_preserved(self):
        builder = _make_builder(opening_balance_account_missing=True)
        result = builder.build()

        assert result.opening_balance_account_missing is True

    def test_synced_at_preserved(self):
        builder = _make_builder()
        result = builder.build()

        assert result.synced_at == _SYNCED_AT


# ---------------------------------------------------------------------------
# FrozenInstanceError on mutation
# ---------------------------------------------------------------------------


class TestFrozenInstanceError:
    """Attempting to mutate any field on the built result raises FrozenInstanceError."""

    def test_cannot_mutate_total_imported(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.total_imported = 99  # type: ignore[misc]

    def test_cannot_mutate_total_fetched(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.total_fetched = 99  # type: ignore[misc]

    def test_cannot_mutate_account_stats(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.account_stats = ()  # type: ignore[misc]

    def test_cannot_mutate_errors(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.errors = ()  # type: ignore[misc]

    def test_cannot_mutate_opening_balances(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.opening_balances = ()  # type: ignore[misc]

    def test_cannot_mutate_synced_at(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.synced_at = datetime.now(tz=timezone.utc)  # type: ignore[misc]

    def test_cannot_mutate_auto_post(self):
        result = _make_builder().build()

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.auto_post = True  # type: ignore[misc]
