"""Sync period resolver.

Computes :class:`SyncPeriod` windows for the sync stack. Provides two modes:

* :meth:`resolve_fixed` — non-adaptive ``today - days .. today`` window.
* :meth:`resolve_adaptive_for` — walks per-IBAN import history and returns
  the next-day-after-last-success window, falling back to ``today - 90``
  when no successful import exists for the IBAN.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Optional

from swen.application.dtos.integration.sync_period import SyncPeriod
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.time import today_utc

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.integration.entities import TransactionImport
    from swen.domain.integration.repositories import TransactionImportRepository


_ADAPTIVE_FALLBACK_DAYS = 90


class SyncPeriodResolver:
    """Resolve fixed and adaptive sync windows."""

    def __init__(self, import_repo: TransactionImportRepository) -> None:
        self._import_repo = import_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SyncPeriodResolver:
        """Build the resolver via the repository factory."""
        return cls(import_repo=factory.import_repository())

    def resolve_fixed(self, days: int) -> SyncPeriod:
        """Return a non-adaptive window ``today - days .. today``."""
        end = today_utc()
        start = end - timedelta(days=days)
        return SyncPeriod(start_date=start, end_date=end, adaptive=False)

    async def resolve_adaptive_for(self, iban: str) -> SyncPeriod:
        """Return an adaptive window based on the last successful import.

        Walks import history for ``iban``. When at least one successful
        import is found, ``start_date`` is the day after the latest known
        booking date (capped at today). When no successful import exists,
        ``start_date`` falls back to ``today - 90 days``.
        """
        end = today_utc()
        imports = await self._import_repo.find_by_iban(iban)

        candidate_dates: list[date] = []
        for record in imports:
            if record.status != ImportStatus.SUCCESS:
                continue

            booking_date = self._extract_booking_date(record)
            if booking_date is not None:
                candidate_dates.append(booking_date)
            elif record.imported_at is not None:
                candidate_dates.append(record.imported_at.date())

        if not candidate_dates:
            start = end - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)
            return SyncPeriod(start_date=start, end_date=end, adaptive=True)

        next_sync_start = max(candidate_dates) + timedelta(days=1)
        start = min(next_sync_start, end)
        return SyncPeriod(start_date=start, end_date=end, adaptive=True)

    @staticmethod
    def _extract_booking_date(record: TransactionImport) -> Optional[date]:
        """Extract a booking date from the import record's identity hash.

        The legacy identity hash on an import record is formatted as
        ``"<hash>|<YYYY-MM-DD>|..."``; the second segment carries the
        booking date. Returns ``None`` when the segment is absent or
        cannot be parsed.
        """
        identity = getattr(record, "bank_transaction_identity", "")
        parts = identity.split("|")

        if len(parts) < 2:
            return None

        try:
            return date.fromisoformat(parts[1])
        except ValueError:
            return None
