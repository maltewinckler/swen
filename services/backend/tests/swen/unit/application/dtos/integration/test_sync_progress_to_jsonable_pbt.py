"""Property-based tests for _to_jsonable round-trip over sync progress events.

**Validates: Requirements 2.3**

Property: for any event built from (UUID, datetime, Decimal, Enum) fields,
json.loads(json.dumps(event.to_dict())) == event.to_dict()
modulo Decimal → float precision (Decimals are already converted to float by
_to_jsonable before the round-trip, so the comparison is exact after that).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from swen.application.dtos.integration.sync_progress import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    BatchSyncCompletedEvent,
    BatchSyncFailedEvent,
    BatchSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
    ErrorCode,
    TransactionClassifiedEvent,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_MIN_DT = datetime(2000, 1, 1, tzinfo=UTC)
_MAX_DT = datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC)


def _iban_strategy() -> st.SearchStrategy[str]:
    return st.just("DE89370400440532013000")


def _uuid_strategy() -> st.SearchStrategy[UUID]:
    return st.uuids()


def _error_code_strategy() -> st.SearchStrategy[ErrorCode]:
    return st.sampled_from(list(ErrorCode))


def _non_negative_int(max_value: int = 10_000) -> st.SearchStrategy[int]:
    return st.integers(min_value=0, max_value=max_value)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_json_roundtrip(event_dict: dict) -> None:
    """Assert that json.loads(json.dumps(d)) == d for the given dict."""
    serialized = json.dumps(event_dict)
    deserialized = json.loads(serialized)
    assert deserialized == event_dict, (
        f"Round-trip mismatch.\nOriginal:     {event_dict}\nDeserialized: {deserialized}"
    )


# ---------------------------------------------------------------------------
# BatchSyncStartedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(total_accounts=_non_negative_int())
def test_batch_sync_started_event_roundtrip(total_accounts: int) -> None:
    """BatchSyncStartedEvent.to_dict() survives a JSON round-trip."""
    event = BatchSyncStartedEvent(total_accounts=total_accounts)
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# BatchSyncCompletedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    total_imported=_non_negative_int(),
    total_skipped=_non_negative_int(),
    total_failed=_non_negative_int(),
    accounts_synced=_non_negative_int(),
)
def test_batch_sync_completed_event_roundtrip(
    total_imported: int,
    total_skipped: int,
    total_failed: int,
    accounts_synced: int,
) -> None:
    """BatchSyncCompletedEvent.to_dict() survives a JSON round-trip."""
    event = BatchSyncCompletedEvent(
        total_imported=total_imported,
        total_skipped=total_skipped,
        total_failed=total_failed,
        accounts_synced=accounts_synced,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# BatchSyncFailedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    code=_error_code_strategy(),
    error_key=st.text(
        min_size=0,
        max_size=100,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
    ),
)
def test_batch_sync_failed_event_roundtrip(code: ErrorCode, error_key: str) -> None:
    """BatchSyncFailedEvent.to_dict() survives a JSON round-trip."""
    event = BatchSyncFailedEvent(code=code, error_key=error_key)
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# AccountSyncStartedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    account_index=_non_negative_int(max_value=100),
    total_accounts=_non_negative_int(max_value=100),
)
def test_account_sync_started_event_roundtrip(
    account_index: int,
    total_accounts: int,
) -> None:
    """AccountSyncStartedEvent.to_dict() survives a JSON round-trip."""
    event = AccountSyncStartedEvent(
        iban="DE89370400440532013000",
        account_name="Test Account",
        account_index=account_index,
        total_accounts=total_accounts,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# AccountSyncFetchedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    transactions_fetched=_non_negative_int(),
    new_transactions=_non_negative_int(),
)
def test_account_sync_fetched_event_roundtrip(
    transactions_fetched: int,
    new_transactions: int,
) -> None:
    """AccountSyncFetchedEvent.to_dict() survives a JSON round-trip."""
    event = AccountSyncFetchedEvent(
        iban="DE89370400440532013000",
        transactions_fetched=transactions_fetched,
        new_transactions=new_transactions,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# AccountSyncCompletedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    imported=_non_negative_int(),
    skipped=_non_negative_int(),
    failed=_non_negative_int(),
)
def test_account_sync_completed_event_roundtrip(
    imported: int,
    skipped: int,
    failed: int,
) -> None:
    """AccountSyncCompletedEvent.to_dict() survives a JSON round-trip."""
    event = AccountSyncCompletedEvent(
        iban="DE89370400440532013000",
        imported=imported,
        skipped=skipped,
        failed=failed,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# AccountSyncFailedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    code=_error_code_strategy(),
    error_key=st.text(
        min_size=0,
        max_size=100,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
    ),
)
def test_account_sync_failed_event_roundtrip(code: ErrorCode, error_key: str) -> None:
    """AccountSyncFailedEvent.to_dict() survives a JSON round-trip."""
    event = AccountSyncFailedEvent(
        iban="DE89370400440532013000",
        code=code,
        error_key=error_key,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# TransactionClassifiedEvent (contains Optional[UUID])
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    transaction_id=st.one_of(st.none(), _uuid_strategy()),
    current=_non_negative_int(max_value=1_000),
    total=_non_negative_int(max_value=1_000),
)
def test_transaction_classified_event_roundtrip(
    transaction_id: UUID | None,
    current: int,
    total: int,
) -> None:
    """TransactionClassifiedEvent.to_dict() survives a JSON round-trip."""
    event = TransactionClassifiedEvent(
        iban="DE89370400440532013000",
        current=current,
        total=total,
        description="Test transaction",
        counter_account_name="Test Account",
        transaction_id=transaction_id,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# ClassificationStartedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(iban=_iban_strategy())
def test_classification_started_event_roundtrip(iban: str) -> None:
    """ClassificationStartedEvent.to_dict() survives a JSON round-trip."""
    event = ClassificationStartedEvent(iban=iban)
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# ClassificationProgressEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    current=_non_negative_int(max_value=1_000),
    total=_non_negative_int(max_value=1_000),
)
def test_classification_progress_event_roundtrip(current: int, total: int) -> None:
    """ClassificationProgressEvent.to_dict() survives a JSON round-trip."""
    event = ClassificationProgressEvent(
        iban="DE89370400440532013000",
        current=current,
        total=total,
    )
    _assert_json_roundtrip(event.to_dict())


# ---------------------------------------------------------------------------
# ClassificationCompletedEvent
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    total=_non_negative_int(max_value=1_000),
    recurring_detected=_non_negative_int(max_value=1_000),
    merchants_extracted=_non_negative_int(max_value=1_000),
    processing_time_ms=_non_negative_int(max_value=100_000),
)
def test_classification_completed_event_roundtrip(
    total: int,
    recurring_detected: int,
    merchants_extracted: int,
    processing_time_ms: int,
) -> None:
    """ClassificationCompletedEvent.to_dict() survives a JSON round-trip."""
    event = ClassificationCompletedEvent(
        iban="DE89370400440532013000",
        total=total,
        recurring_detected=recurring_detected,
        merchants_extracted=merchants_extracted,
        processing_time_ms=processing_time_ms,
    )
    _assert_json_roundtrip(event.to_dict())
