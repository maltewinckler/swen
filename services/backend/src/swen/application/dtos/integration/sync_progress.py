"""Sync progress events for SSE streaming."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class SyncEventType(str, Enum):
    """Types of sync progress events."""

    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"

    ACCOUNT_STARTED = "account_started"
    ACCOUNT_FETCHING = "account_fetching"
    ACCOUNT_FETCHED = "account_fetched"
    ACCOUNT_CLASSIFYING = "account_classifying"
    ACCOUNT_COMPLETED = "account_completed"
    ACCOUNT_FAILED = "account_failed"

    # ML Classification events (batch)
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_PROGRESS = "classification_progress"
    CLASSIFICATION_COMPLETED = "classification_completed"

    TRANSACTION_CLASSIFIED = "transaction_classified"
    TRANSACTION_SKIPPED = "transaction_skipped"
    TRANSACTION_FAILED = "transaction_failed"


@dataclass
class SyncProgressEvent:
    """Base class for sync progress events."""

    event_type: SyncEventType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SyncStartedEvent(SyncProgressEvent):
    """Emitted when sync begins."""

    total_accounts: int = 0

    def __init__(self, total_accounts: int, message: Optional[str] = None):
        super().__init__(
            event_type=SyncEventType.SYNC_STARTED,
            message=message or f"Starting sync for {total_accounts} account(s)",
        )
        self.total_accounts = total_accounts

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["total_accounts"] = self.total_accounts
        return d


@dataclass
class SyncCompletedEvent(SyncProgressEvent):
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
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.SYNC_COMPLETED,
            message=message
            or f"Sync complete: {total_imported} imported, {total_skipped} skipped",
        )
        self.total_imported = total_imported
        self.total_skipped = total_skipped
        self.total_failed = total_failed
        self.accounts_synced = accounts_synced

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["total_imported"] = self.total_imported
        d["total_skipped"] = self.total_skipped
        d["total_failed"] = self.total_failed
        d["accounts_synced"] = self.accounts_synced
        return d


@dataclass
class SyncFailedEvent(SyncProgressEvent):
    """Emitted when sync fails with an error."""

    error: str = ""

    def __init__(self, error: str, message: Optional[str] = None):
        super().__init__(
            event_type=SyncEventType.SYNC_FAILED,
            message=message or f"Sync failed: {error}",
        )
        self.error = error

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["error"] = self.error
        return d


@dataclass
class AccountStartedEvent(SyncProgressEvent):
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
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_STARTED,
            message=message
            or f"Syncing {account_name} ({account_index}/{total_accounts})",
        )
        self.iban = iban
        self.account_name = account_name
        self.account_index = account_index
        self.total_accounts = total_accounts

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["account_name"] = self.account_name
        d["account_index"] = self.account_index
        d["total_accounts"] = self.total_accounts
        return d


@dataclass
class AccountFetchedEvent(SyncProgressEvent):
    """Emitted after fetching transactions from bank."""

    iban: str = ""
    transactions_fetched: int = 0
    new_transactions: int = 0

    def __init__(
        self,
        iban: str,
        transactions_fetched: int,
        new_transactions: int,
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_FETCHED,
            message=message
            or f"Fetched {transactions_fetched} transactions ({new_transactions} new)",
        )
        self.iban = iban
        self.transactions_fetched = transactions_fetched
        self.new_transactions = new_transactions

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["transactions_fetched"] = self.transactions_fetched
        d["new_transactions"] = self.new_transactions
        return d


@dataclass
class AccountClassifyingEvent(SyncProgressEvent):
    """Emitted when starting to classify transactions for an account."""

    iban: str = ""
    current: int = 0
    total: int = 0

    def __init__(
        self,
        iban: str,
        current: int,
        total: int,
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_CLASSIFYING,
            message=message or f"Classifying {current}/{total}",
        )
        self.iban = iban
        self.current = current
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["current"] = self.current
        d["total"] = self.total
        return d


@dataclass
class AccountCompletedEvent(SyncProgressEvent):
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
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_COMPLETED,
            message=message or f"Completed: {imported} imported, {skipped} skipped",
        )
        self.iban = iban
        self.imported = imported
        self.skipped = skipped
        self.failed = failed

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["imported"] = self.imported
        d["skipped"] = self.skipped
        d["failed"] = self.failed
        return d


@dataclass
class AccountFailedEvent(SyncProgressEvent):
    """Emitted when account sync fails."""

    iban: str = ""
    error: str = ""

    def __init__(self, iban: str, error: str, message: Optional[str] = None):
        super().__init__(
            event_type=SyncEventType.ACCOUNT_FAILED,
            message=message or f"Failed: {error}",
        )
        self.iban = iban
        self.error = error

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["error"] = self.error
        return d


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
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.TRANSACTION_CLASSIFIED,
            message=message or f"Classified {current}/{total}: {description[:30]}...",
        )
        self.iban = iban
        self.transaction_id = transaction_id
        self.description = description
        self.counter_account_name = counter_account_name
        self.current = current
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["transaction_id"] = str(self.transaction_id) if self.transaction_id else None
        d["description"] = self.description
        d["counter_account_name"] = self.counter_account_name
        d["current"] = self.current
        d["total"] = self.total
        return d


# -----------------------------------------------------------------------------
# ML Classification Events (Batch)
# -----------------------------------------------------------------------------


@dataclass
class ClassificationStartedEvent(SyncProgressEvent):
    """Emitted when ML batch classification begins."""

    iban: str = ""
    total: int = 0

    def __init__(
        self,
        iban: str,
        total: int,
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_STARTED,
            message=message or f"Classifying {total} transactions...",
        )
        self.iban = iban
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["total"] = self.total
        return d


@dataclass
class ClassificationProgressEvent(SyncProgressEvent):
    """Emitted during ML batch classification for progress updates."""

    iban: str = ""
    current: int = 0
    total: int = 0
    last_tier: Optional[str] = None
    last_merchant: Optional[str] = None

    def __init__(  # noqa: PLR0913
        self,
        iban: str,
        current: int,
        total: int,
        last_tier: Optional[str] = None,
        last_merchant: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_PROGRESS,
            message=message or f"Classifying {current}/{total}",
        )
        self.iban = iban
        self.current = current
        self.total = total
        self.last_tier = last_tier
        self.last_merchant = last_merchant

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["current"] = self.current
        d["total"] = self.total
        d["last_tier"] = self.last_tier
        d["last_merchant"] = self.last_merchant
        return d


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
        message: Optional[str] = None,
    ):
        super().__init__(
            event_type=SyncEventType.CLASSIFICATION_COMPLETED,
            message=message or f"Classified {total} transactions",
        )
        self.iban = iban
        self.total = total
        self.by_tier = by_tier or {}
        self.recurring_detected = recurring_detected
        self.merchants_extracted = merchants_extracted
        self.processing_time_ms = processing_time_ms

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["iban"] = self.iban
        d["total"] = self.total
        d["by_tier"] = self.by_tier
        d["recurring_detected"] = self.recurring_detected
        d["merchants_extracted"] = self.merchants_extracted
        d["processing_time_ms"] = self.processing_time_ms
        return d
