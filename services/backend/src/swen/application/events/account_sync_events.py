"""Per-account sync lifecycle events and transaction classification event."""

from __future__ import annotations

from dataclasses import dataclass, field

from swen.application.events.base import ErrorCode, SyncEventType, SyncProgressEvent


@dataclass
class AccountSyncStartedEvent(SyncProgressEvent):
    """Emitted when starting to sync a specific account."""

    event_type: SyncEventType = field(
        default=SyncEventType.ACCOUNT_SYNC_STARTED, init=False
    )
    iban: str = ""
    account_name: str = ""
    account_index: int = 0
    total_accounts: int = 0


@dataclass
class AccountSyncFetchedEvent(SyncProgressEvent):
    """Emitted after fetching transactions from bank."""

    event_type: SyncEventType = field(
        default=SyncEventType.ACCOUNT_SYNC_FETCHED, init=False
    )
    iban: str = ""
    transactions_fetched: int = 0
    new_transactions: int = 0


@dataclass
class AccountSyncCompletedEvent(SyncProgressEvent):
    """Emitted when account sync completes."""

    event_type: SyncEventType = field(
        default=SyncEventType.ACCOUNT_SYNC_COMPLETED, init=False
    )
    iban: str = ""
    imported: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class AccountSyncFailedEvent(SyncProgressEvent):
    """Emitted when account sync fails."""

    event_type: SyncEventType = field(
        default=SyncEventType.ACCOUNT_SYNC_FAILED, init=False
    )
    iban: str = ""
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    error_key: str = ""
