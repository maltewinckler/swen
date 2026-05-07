"""Property-based tests for SyncPeriod.widen monotonicity and idempotence.

**Validates: Requirements 8.7**

Properties tested:
1. Non-adaptive: widen always returns the same object (identity / no-op).
2. Adaptive monotonicity: sequential widen calls are equivalent to a single
   widen over the combined extremes.
3. Adaptive idempotence: widening with the current bounds returns an equal
   (though not necessarily identical) period.
"""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from swen.application.dtos.integration.sync_period import SyncPeriod

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_MIN_DATE = date(2000, 1, 1)
_MAX_DATE = date(2099, 12, 31)


def _date_strategy() -> st.SearchStrategy[date]:
    return st.dates(min_value=_MIN_DATE, max_value=_MAX_DATE)


def _sync_period_strategy(
    *, adaptive: bool | None = None
) -> st.SearchStrategy[SyncPeriod]:
    """Build a SyncPeriod with start_date <= end_date."""
    adaptive_st = st.just(adaptive) if adaptive is not None else st.booleans()
    return st.builds(
        _make_period,
        start=_date_strategy(),
        delta_days=st.integers(min_value=0, max_value=365),
        adaptive=adaptive_st,
    )


def _make_period(start: date, delta_days: int, adaptive: bool) -> SyncPeriod:
    return SyncPeriod(
        start_date=start,
        end_date=start + timedelta(days=delta_days),
        adaptive=adaptive,
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    period=_sync_period_strategy(adaptive=False),
    obs_start=_date_strategy(),
    obs_end=_date_strategy(),
)
def test_non_adaptive_widen_returns_self(
    period: SyncPeriod,
    obs_start: date,
    obs_end: date,
) -> None:
    """For non-adaptive periods, widen(s, e) is the same object (identity)."""
    result = period.widen(obs_start, obs_end)
    assert result is period


@settings(max_examples=100)
@given(
    period=_sync_period_strategy(adaptive=True),
    s1=_date_strategy(),
    e1=_date_strategy(),
    s2=_date_strategy(),
    e2=_date_strategy(),
)
def test_adaptive_sequential_widen_equals_combined_widen(
    period: SyncPeriod,
    s1: date,
    e1: date,
    s2: date,
    e2: date,
) -> None:
    """p.widen(s1, e1).widen(s2, e2) == p.widen(min(s1,s2), max(e1,e2)) for adaptive."""
    sequential = period.widen(s1, e1).widen(s2, e2)
    combined = period.widen(min(s1, s2), max(e1, e2))

    assert sequential == combined


@settings(max_examples=100)
@given(period=_sync_period_strategy(adaptive=True))
def test_adaptive_widen_with_own_bounds_is_equal(period: SyncPeriod) -> None:
    """Widening an adaptive period with its own bounds returns an equal period."""
    result = period.widen(period.start_date, period.end_date)
    assert result == period


@settings(max_examples=100)
@given(
    period=_sync_period_strategy(adaptive=True),
    obs_start=_date_strategy(),
    obs_end=_date_strategy(),
)
def test_adaptive_widen_start_is_min(
    period: SyncPeriod,
    obs_start: date,
    obs_end: date,
) -> None:
    """After widen, start_date == min(period.start_date, obs_start)."""
    result = period.widen(obs_start, obs_end)
    assert result.start_date == min(period.start_date, obs_start)


@settings(max_examples=100)
@given(
    period=_sync_period_strategy(adaptive=True),
    obs_start=_date_strategy(),
    obs_end=_date_strategy(),
)
def test_adaptive_widen_end_is_max(
    period: SyncPeriod,
    obs_start: date,
    obs_end: date,
) -> None:
    """After widen, end_date == max(period.end_date, obs_end)."""
    result = period.widen(obs_start, obs_end)
    assert result.end_date == max(period.end_date, obs_end)


@settings(max_examples=100)
@given(
    period=_sync_period_strategy(adaptive=True),
    obs_start=_date_strategy(),
    obs_end=_date_strategy(),
)
def test_adaptive_widen_preserves_adaptive_flag(
    period: SyncPeriod,
    obs_start: date,
    obs_end: date,
) -> None:
    """Widening an adaptive period always returns an adaptive period."""
    result = period.widen(obs_start, obs_end)
    assert result.adaptive is True
