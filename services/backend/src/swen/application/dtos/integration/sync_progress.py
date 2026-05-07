"""Sync progress events for SSE streaming."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
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

    # ML Classification events (batch)
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_PROGRESS = "classification_progress"
    CLASSIFICATION_COMPLETED = "classification_completed"

    TRANSACTION_CLASSIFIED = "transaction_classified"

    # Reclassification events (draft re-ML)
    RECLASSIFY_STARTED = "reclassify_started"
    RECLASSIFY_PROGRESS = "reclassify_progress"
    RECLASSIFY_TRANSACTION = "reclassify_transaction"
    RECLASSIFY_COMPLETED = "reclassify_completed"
    RECLASSIFY_FAILED = "reclassify_failed"


@dataclass
class SyncProgressEvent:
    """Base class for sync progress events."""

    event_type: SyncEventType
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(self).items()}


@dataclass
class BatchSyncStartedEvent(SyncProgressEvent):
    """Emitted when sync begins."""

    total_accounts: int = 0

    def __init__(self, total_accounts: int):
        super().__init__(
            event_type=SyncEventType.BATCH_SYNC_STARTED,
        )
        self.total_accounts = total_accounts


@dataclass
class BatchSyncCompletedEvent(SyncProgressEvent):
    """Emitted when sync completes successfully."""

    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    accounts_synced: int = 0

    def __init__(
        self,
        total_imported: int,
        total_skipped: int,
        total_failed: int,
        accounts_synced: int,
    ):
        super().__init__(
            event_type=SyncEventType.BATCH_SYNC_COMPLETED,
        )
        self.total_imported = total_imported
        self.total_skipped = total_skipped
        self.total_failed = total_failed
        self.accounts_synced = accounts_synced


@dataclass
class BatchSyncFailedEvent(SyncProgressEvent):
    """Emitted when the entire batch sync fails."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    error_key: str = ""

    def __init__(self, code: ErrorCode, error_key: str):
        super().__init__(
            event_type=SyncEventType.BATCH_SYNC_FAILED,
        )
        self.code = code
        self.error_key = error_key


@dataclass
class AccountSyncStartedEvent(SyncProgressEvent):
    """Emitted when starting to sync a specific account."""

    iban: str = ""
    account_name: str = ""
    account_index: int = 0
    total_accounts: int = 0

    def __init__(
        self,
        iban: str,
        account_name: str,
        account_index: int,
        total_accounts: int,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_SYNC_STARTED,
        )
        self.iban = iban
        self.account_name = account_name
        self.account_index = account_index
        self.total_accounts = total_accounts


@dataclass
class AccountSyncFetchedEvent(SyncProgressEvent):
    """Emitted after fetching transactions from bank."""

    iban: str = ""
    transactions_fetched: int = 0
    new_transactions: int = 0

    def __init__(
        self,
        iban: str,
        transactions_fetched: int,
        new_transactions: int,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_SYNC_FETCHED,
        )
        self.iban = iban
        self.transactions_fetched = transactions_fetched
        self.new_transactions = new_transactions


@dataclass
class AccountSyncCompletedEvent(SyncProgressEvent):
    """Emitted when account sync completes."""

    iban: str = ""
    imported: int = 0
    skipped: int = 0
    failed: int = 0

    def __init__(
        self,
        iban: str,
        imported: int,
        skipped: int,
        failed: int,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_SYNC_COMPLETED,
        )
        self.iban = iban
        self.imported = imported
        self.skipped = skipped
        self.failed = failed


@dataclass
class AccountSyncFailedEvent(SyncProgressEvent):
    """Emitted when account sync fails."""

    iban: str = ""
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    error_key: str = ""

    def __init__(self, iban: str, code: ErrorCode, error_key: str):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_SYNC_FAILED,
        )
        self.iban = iban
        self.code = code
        self.error_key = error_key


@dataclass
class TransactionClassifiedEvent(SyncProgressEvent):
    """Emitted when a transaction is successfully classified and imported."""

    iban: str = ""
    transaction_id: Optional[UUID] = None
    description: str = ""
    counter_account_name: str = ""
    current: int = 0
    total: int = 0

    def __init__(  # NOQA: PLR0913
        self,
        iban: str,
        current: int,
        total: int,
        description: str = "",
        counter_account_name: str = "",
        transaction_id: Optional[UUID] = None,
    ):
        super().__init__(
            event_type=SyncEventType.TRANSACTION_CLASSIFIED,
        )
        self.iban = iban
        self.transaction_id = transaction_id
        self.description = description
        self.counter_account_name = counter_account_name
        self.current = current
        self.total = total


# -----------------------------------------------------------------------------
# ML Classification Events (Batch)
# -----------------------------------------------------------------------------


@dataclass
class ClassificationStartedEvent(SyncProgressEvent):
    """Emitted when ML batch classification begins."""

    iban: str = ""

    def __init__(
        self,
        iban: str,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_STARTED,
        )
        self.iban = iban


@dataclass
class ClassificationProgressEvent(SyncProgressEvent):
    """Emitted during ML batch classification for progress updates."""

    iban: str = ""
    current: int = 0
    total: int = 0
    last_tier: Optional[str] = None
    last_merchant: Optional[str] = None

    def __init__(
        self,
        iban: str,
        current: int,
        total: int,
        last_tier: Optional[str] = None,
        last_merchant: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_PROGRESS,
        )
        self.iban = iban
        self.current = current
        self.total = total
        self.last_tier = last_tier
        self.last_merchant = last_merchant


@dataclass
class ClassificationCompletedEvent(SyncProgressEvent):
    """Emitted when ML batch classification completes."""

    iban: str = ""
    total: int = 0
    by_tier: dict = field(default_factory=dict)
    recurring_detected: int = 0
    merchants_extracted: int = 0
    processing_time_ms: int = 0

    def __init__(  # noqa: PLR0913
        self,
        iban: str,
        total: int,
        by_tier: Optional[dict] = None,
        recurring_detected: int = 0,
        merchants_extracted: int = 0,
        processing_time_ms: int = 0,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_COMPLETED,
        )
        self.iban = iban
        self.total = total
        self.by_tier = by_tier or {}
        self.recurring_detected = recurring_detected
        self.merchants_extracted = merchants_extracted
        self.processing_time_ms = processing_time_ms
