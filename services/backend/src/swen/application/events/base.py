"""Base class and enums for application-layer sync progress events."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


def _utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


def _to_jsonable(value):
    """Convert a value to a JSON-serializable form."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


class ErrorCode(str, Enum):
    """Structured error codes for sync failure events."""

    BANK_CONNECTION_ERROR = "bank_connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    TAN_ERROR = "tan_error"
    INTERNAL_ERROR = "internal_error"
    INACTIVE_MAPPING = "inactive_mapping"
    CREDENTIALS_NOT_FOUND = "credentials_not_found"
    TIMEOUT_ERROR = "timeout_error"


class SyncEventType(str, Enum):
    """Types of sync progress events."""

    BATCH_SYNC_STARTED = "batch_sync_started"
    BATCH_SYNC_COMPLETED = "batch_sync_completed"
    BATCH_SYNC_FAILED = "batch_sync_failed"

    ACCOUNT_SYNC_STARTED = "account_sync_started"
    ACCOUNT_SYNC_FETCHED = "account_sync_fetched"
    ACCOUNT_SYNC_COMPLETED = "account_sync_completed"
    ACCOUNT_SYNC_FAILED = "account_sync_failed"

    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_PROGRESS = "classification_progress"
    CLASSIFICATION_COMPLETED = "classification_completed"

    RECLASSIFY_STARTED = "reclassify_started"
    RECLASSIFY_PROGRESS = "reclassify_progress"
    RECLASSIFY_TRANSACTION = "reclassify_transaction"
    RECLASSIFY_COMPLETED = "reclassify_completed"
    RECLASSIFY_FAILED = "reclassify_failed"

    RESULT = "result"


@dataclass
class SyncProgressEvent:
    """Base class for sync progress events."""

    event_type: SyncEventType
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(self).items()}
