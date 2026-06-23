"""Sync period resolver.

Computes :class:`SyncPeriod` windows for the sync stack. Provides two modes:

* :meth:`resolve_fixed`: non-adaptive ``today - days .. today`` window.
* :meth:`resolve_adaptive_for`: returns the next-day-after-last-success window
  based on the latest booking date stored on successful import records for the
  IBAN, falling back to ``today - 90`` when no successful import exists.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from swen.domain.integration.value_objects.sync_period import SyncPeriod
from swen.domain.shared.time import today_utc

_ADAPTIVE_FALLBACK_DAYS = 90


class SyncPeriodResolver:
    """Resolve fixed and adaptive sync windows."""

    @staticmethod
    def resolve_period(latest: Optional[date], days: Optional[int]) -> SyncPeriod:
        """Resolve the sync period based on the situation.

        Priority:
        1. If a fixed days value is provided, return the fixed window.
        2. If a latest booking date is available, return the adaptive window.
        3. Otherwise, return the fallback adaptive window.
        """
        if days is not None:
            period = SyncPeriodResolver._resolve_fixed(days)
        elif latest is not None:
            period = SyncPeriodResolver._resolve_adaptive(latest)
        else:
            period = SyncPeriodResolver._resolve_fallback()
        return period

    @staticmethod
    def _resolve_fixed(days: int) -> SyncPeriod:
        """Return a non-adaptive window ``today - days .. today``."""
        end = today_utc()
        start = end - timedelta(days=days)
        return SyncPeriod(start_date=start, end_date=end, adaptive=False)

    @staticmethod
    def _resolve_adaptive(latest: date) -> SyncPeriod:
        """Return an adaptive window based on the last successful import.

        Queries the latest booking date among all successful imports for
        ``iban``. When found, ``start_date`` is the day after that date
        (capped at today). When no successful import exists, ``start_date``
        falls back to ``today - 90 days``.
        """
        end = today_utc()
        start = min(latest + timedelta(days=1), end)
        return SyncPeriod(start_date=start, end_date=end, adaptive=True)

    @staticmethod
    def _resolve_fallback() -> SyncPeriod:
        """Return a fallback adaptive window of ``today - 90 days .. today``."""
        end = today_utc()
        start = end - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)
        return SyncPeriod(start_date=start, end_date=end, adaptive=True)
