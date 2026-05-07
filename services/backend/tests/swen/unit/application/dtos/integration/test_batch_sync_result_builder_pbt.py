"""Property-based tests for BatchSyncResultBuilder aggregation conservation.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

Conservation invariant: for any list of SyncResult inputs, the builder's
aggregate totals must equal the sum of the corresponding per-account fields.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from swen.application.dtos.integration.batch_sync_result import BatchSyncResultBuilder
from swen.application.dtos.integration.sync_result import SyncResult

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_SYNCED_AT = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
_START = date(2024, 6, 1)
_END = date(2024, 6, 15)


def _sync_result_strategy() -> st.SearchStrategy[SyncResult]:
    """Build a SyncResult with non-negative integer transaction counts."""
    return st.builds(
        SyncResult,
        success=st.booleans(),
        synced_at=st.just(_SYNCED_AT),
        iban=st.just("DE89370400440532013000"),
        start_date=st.just(_START),
        end_date=st.just(_END),
        transactions_fetched=st.integers(min_value=0, max_value=10_000),
        transactions_imported=st.integers(min_value=0, max_value=10_000),
        transactions_skipped=st.integers(min_value=0, max_value=10_000),
        transactions_failed=st.integers(min_value=0, max_value=10_000),
        transactions_reconciled=st.integers(min_value=0, max_value=10_000),
        error_message=st.none(),
        warning_message=st.none(),
        opening_balance_created=st.just(False),
        opening_balance_amount=st.none(),
    )


def _make_builder() -> BatchSyncResultBuilder:
    return BatchSyncResultBuilder(
        synced_at=_SYNCED_AT,
        start_date=_START,
        end_date=_END,
        auto_post=False,
        opening_balance_account_missing=False,
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(inputs=st.lists(_sync_result_strategy(), min_size=0, max_size=20))
def test_total_imported_conservation(inputs: list[SyncResult]) -> None:
    """total_imported == sum(r.transactions_imported for r in inputs)."""
    builder = _make_builder()
    for r in inputs:
        builder.add_account(r)
    result = builder.build()

    assert result.total_imported == sum(r.transactions_imported for r in inputs)


@settings(max_examples=100)
@given(inputs=st.lists(_sync_result_strategy(), min_size=0, max_size=20))
def test_total_skipped_conservation(inputs: list[SyncResult]) -> None:
    """total_skipped == sum(r.transactions_skipped for r in inputs)."""
    builder = _make_builder()
    for r in inputs:
        builder.add_account(r)
    result = builder.build()

    assert result.total_skipped == sum(r.transactions_skipped for r in inputs)


@settings(max_examples=100)
@given(inputs=st.lists(_sync_result_strategy(), min_size=0, max_size=20))
def test_total_failed_conservation(inputs: list[SyncResult]) -> None:
    """total_failed == sum(r.transactions_failed for r in inputs)."""
    builder = _make_builder()
    for r in inputs:
        builder.add_account(r)
    result = builder.build()

    assert result.total_failed == sum(r.transactions_failed for r in inputs)


@settings(max_examples=100)
@given(inputs=st.lists(_sync_result_strategy(), min_size=0, max_size=20))
def test_total_fetched_conservation(inputs: list[SyncResult]) -> None:
    """total_fetched == sum(r.transactions_fetched for r in inputs)."""
    builder = _make_builder()
    for r in inputs:
        builder.add_account(r)
    result = builder.build()

    assert result.total_fetched == sum(r.transactions_fetched for r in inputs)


@settings(max_examples=100)
@given(inputs=st.lists(_sync_result_strategy(), min_size=0, max_size=20))
def test_account_stats_length_equals_input_length(inputs: list[SyncResult]) -> None:
    """account_stats has exactly one entry per add_account call."""
    builder = _make_builder()
    for r in inputs:
        builder.add_account(r)
    result = builder.build()

    assert len(result.account_stats) == len(inputs)
