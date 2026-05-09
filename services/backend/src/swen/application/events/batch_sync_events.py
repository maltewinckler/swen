"""Batch sync lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, field

from swen.application.events.base import ErrorCode, SyncEventType, SyncProgressEvent


@dataclass
class BatchSyncStartedEvent(SyncProgressEvent):
    """Emitted when sync begins."""

    event_type: SyncEventType = field(
        default=SyncEventType.BATCH_SYNC_STARTED, init=False
    )
    total_accounts: int = 0


@dataclass
class BatchSyncCompletedEvent(SyncProgressEvent):
    """Emitted when sync completes successfully."""

    event_type: SyncEventType = field(
        default=SyncEventType.BATCH_SYNC_COMPLETED, init=False
    )
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    accounts_synced: int = 0


@dataclass
class SyncResultEvent(SyncProgressEvent):
    """Terminal result event: emitted by the command as the last event."""

    event_type: SyncEventType = field(default=SyncEventType.RESULT, init=False)
    success: bool = False
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    accounts_synced: int = 0


@dataclass
class BatchSyncFailedEvent(SyncProgressEvent):
    """Emitted when the entire batch sync fails."""

    event_type: SyncEventType = field(
        default=SyncEventType.BATCH_SYNC_FAILED, init=False
    )
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    error_key: str = ""
