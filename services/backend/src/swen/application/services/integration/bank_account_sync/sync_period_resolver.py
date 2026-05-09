"""Sync period resolver.

Computes :class:`SyncPeriod` windows for the sync stack. Provides two modes:

* :meth:`resolve_fixed`: non-adaptive ``today - days .. today`` window.
* :meth:`resolve_adaptive_for`: returns the next-day-after-last-success window
  based on the latest booking date stored on successful import records for the
  IBAN, falling back to ``today - 90`` when no successful import exists.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from swen.domain.integration.value_objects.sync_period import SyncPeriod
from swen.domain.shared.time import today_utc

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.integration.repositories import TransactionImportRepository


_ADAPTIVE_FALLBACK_DAYS = 90


class SyncPeriodResolver:
    """Resolve fixed and adaptive sync windows."""

    def __init__(self, import_repo: TransactionImportRepository):
        self._import_repo = import_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SyncPeriodResolver:
        return cls(import_repo=factory.import_repository())

    def resolve_fixed(self, days: int) -> SyncPeriod:
        """Return a non-adaptive window ``today - days .. today``."""
        end = today_utc()
        start = end - timedelta(days=days)
        return SyncPeriod(start_date=start, end_date=end, adaptive=False)

    async def resolve_adaptive(self, date_: date) -> SyncPeriod:
        """Return an adaptive window based on the last successful import.

        Queries the latest booking date among all successful imports for
        ``iban``. When found, ``start_date`` is the day after that date
        (capped at today). When no successful import exists, ``start_date``
        falls back to ``today - 90 days``.
        """
        end = today_utc()
        start = min(date_ + timedelta(days=1), end)
        return SyncPeriod(start_date=start, end_date=end, adaptive=True)
