"""Unit tests for SyncPeriodResolver.

Covers:
- resolve_fixed: window math (today - days .. today, non-adaptive)
- resolve_adaptive_for: next-day-after-last-success from import history
- resolve_adaptive_for: today-90-days fallback when no successful import exists
- resolve_adaptive_for: today-90-days fallback when import list is empty
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from swen.application.services.integration.bank_account_sync.sync_period_resolver import (
    _ADAPTIVE_FALLBACK_DAYS,
    SyncPeriodResolver,
)

TEST_IBAN = "DE89370400440532013000"

# Fixed "today" for deterministic tests
_TODAY = date(2024, 6, 15)


def _make_import_repo(latest_booking_date: date | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.find_latest_booking_date_by_iban.return_value = latest_booking_date
    return repo


# ---------------------------------------------------------------------------
# resolve_fixed
# ---------------------------------------------------------------------------


class TestResolveFixed:
    """resolve_fixed returns a non-adaptive window of today - days .. today."""

    def test_start_date_is_today_minus_days(self):
        repo = _make_import_repo()
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=30)

        assert period.start_date == _TODAY - timedelta(days=30)

    def test_end_date_is_today(self):
        repo = _make_import_repo()
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=30)

        assert period.end_date == _TODAY

    def test_period_is_not_adaptive(self):
        repo = _make_import_repo()
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=7)

        assert period.adaptive is False

    def test_window_width_matches_days_parameter(self):
        repo = _make_import_repo()
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=90)

        assert (period.end_date - period.start_date).days == 90

    def test_zero_days_gives_same_start_and_end(self):
        repo = _make_import_repo()
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=0)

        assert period.start_date == period.end_date == _TODAY


# ---------------------------------------------------------------------------
# resolve_adaptive_for — fallback (no successful imports)
# ---------------------------------------------------------------------------


class TestResolveAdaptiveForFallback:
    """Falls back to today - 90 days when no successful import exists."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_imports(self):
        repo = _make_import_repo(None)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == _TODAY - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)
        assert period.end_date == _TODAY

    @pytest.mark.asyncio
    async def test_fallback_period_is_adaptive(self):
        repo = _make_import_repo(None)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.adaptive is True

    @pytest.mark.asyncio
    async def test_calls_find_latest_booking_date_by_iban_with_correct_iban(self):
        repo = _make_import_repo(None)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            await resolver.resolve_adaptive_for(TEST_IBAN)

        repo.find_latest_booking_date_by_iban.assert_awaited_once_with(TEST_IBAN)


# ---------------------------------------------------------------------------
# resolve_adaptive_for — next-day-after-last-success
# ---------------------------------------------------------------------------


class TestResolveAdaptiveForNextDay:
    """Returns next-day-after-last-success when a latest booking date is found."""

    @pytest.mark.asyncio
    async def test_start_is_day_after_latest_booking_date(self):
        last_booking = date(2024, 5, 20)
        repo = _make_import_repo(last_booking)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == last_booking + timedelta(days=1)

    @pytest.mark.asyncio
    async def test_start_capped_at_today_when_next_day_is_in_future(self):
        """If last booking was yesterday, start = today (not tomorrow)."""
        yesterday = _TODAY - timedelta(days=1)
        repo = _make_import_repo(yesterday)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == _TODAY

    @pytest.mark.asyncio
    async def test_end_date_is_always_today(self):
        repo = _make_import_repo(date(2024, 5, 1))
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.end_date == _TODAY

    @pytest.mark.asyncio
    async def test_period_is_adaptive(self):
        repo = _make_import_repo(date(2024, 5, 1))
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.bank_account_sync.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.adaptive is True
