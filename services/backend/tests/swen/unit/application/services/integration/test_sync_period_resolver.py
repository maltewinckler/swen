"""Unit tests for SyncPeriodResolver.

Covers:
- resolve_period with days only (no history): fixed non-adaptive window
- resolve_period with latest booking date: adaptive next-day-after-last-success
- resolve_period with no history and no days: fallback adaptive window (today - 90)
- resolve_period with latest overrides days when both are provided
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from swen.domain.integration.services.sync_period_resolver import (
    _ADAPTIVE_FALLBACK_DAYS,
    SyncPeriodResolver,
)

# Fixed "today" for deterministic tests
_TODAY = date(2024, 6, 15)

_PATCH_TODAY = patch(
    "swen.domain.integration.services.sync_period_resolver.today_utc",
    return_value=_TODAY,
)


# ---------------------------------------------------------------------------
# Fixed window (latest=None, days given)
# ---------------------------------------------------------------------------


class TestResolvePeriodFixed:
    """resolve_period with latest=None and days given returns a non-adaptive window."""

    def test_start_date_is_today_minus_days(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=30)

        assert period.start_date == _TODAY - timedelta(days=30)

    def test_end_date_is_today(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=30)

        assert period.end_date == _TODAY

    def test_period_is_not_adaptive(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=7)

        assert period.adaptive is False

    def test_window_width_matches_days_parameter(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=90)

        assert (period.end_date - period.start_date).days == 90

    def test_zero_days_gives_same_start_and_end(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=0)

        assert period.start_date == period.end_date == _TODAY


# ---------------------------------------------------------------------------
# Fallback adaptive (latest=None, days=None)
# ---------------------------------------------------------------------------


class TestResolvePeriodFallback:
    """Falls back to today - 90 days when no latest booking date and no days."""

    def test_fallback_start_is_today_minus_90(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=None)

        assert period.start_date == _TODAY - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)

    def test_fallback_end_is_today(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=None)

        assert period.end_date == _TODAY

    def test_fallback_period_is_adaptive(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=None, days=None)

        assert period.adaptive is True


# ---------------------------------------------------------------------------
# Adaptive — next-day-after-last-success (latest provided)
# ---------------------------------------------------------------------------


class TestResolvePeriodAdaptive:
    """Returns next-day-after-last-success when a latest booking date is known."""

    def test_start_is_day_after_latest_booking_date(self):
        last_booking = date(2024, 5, 20)

        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=last_booking, days=None)

        assert period.start_date == last_booking + timedelta(days=1)

    def test_start_capped_at_today_when_next_day_is_in_future(self):
        """If last booking was yesterday, start = today (not tomorrow)."""
        yesterday = _TODAY - timedelta(days=1)

        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=yesterday, days=None)

        assert period.start_date == _TODAY

    def test_end_date_is_always_today(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(
                latest=date(2024, 5, 1), days=None
            )

        assert period.end_date == _TODAY

    def test_period_is_adaptive(self):
        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(
                latest=date(2024, 5, 1), days=None
            )

        assert period.adaptive is True

    def test_latest_overrides_days_when_both_provided(self):
        """When latest is known, days is ignored and the adaptive window is used."""
        last_booking = date(2024, 5, 20)

        with _PATCH_TODAY:
            period = SyncPeriodResolver.resolve_period(latest=last_booking, days=30)

        assert period.adaptive is True
        assert period.start_date == last_booking + timedelta(days=1)
