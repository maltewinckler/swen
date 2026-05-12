"""SyncPeriod: sync date range value object.

Carries the (start_date, end_date) window used by the sync stack together
with an adaptive flag. When adaptive is True, callers expand the placeholder
window per-IBAN via SyncPeriodResolver, and may widen the resulting window
to cover the actual range observed on the bank side via SyncPeriod.widen.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date


@dataclass(frozen=True)
class SyncPeriod:
    """Immutable sync window value object.

    Attributes
    ----------
        start_date: Inclusive start of the sync window.
        end_date: Inclusive end of the sync window.
        adaptive: When True, the window is a placeholder to be expanded
            per-IBAN by SyncPeriodResolver and may be widened to cover the
            range actually returned by the bank.
    """

    start_date: date
    end_date: date
    adaptive: bool

    def widen(self, observed_start: date, observed_end: date) -> SyncPeriod:
        """Return a window covering both this period and the observed range.

        For non-adaptive windows the period is returned unchanged: a fixed
        window must not be silently widened. For adaptive windows a new
        SyncPeriod is returned with start_date = min(self.start_date,
        observed_start) and end_date = max(self.end_date, observed_end).
        """
        if not self.adaptive:
            return self
        return replace(
            self,
            start_date=min(self.start_date, observed_start),
            end_date=max(self.end_date, observed_end),
        )
