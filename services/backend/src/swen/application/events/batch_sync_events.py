"""Batch sync lifecycle events."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from swen.application.events.base import ErrorCode, SyncEventType, SyncProgressEvent


class BatchSyncStartedEvent(SyncProgressEvent):
    """Emitted when sync begins."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.BATCH_SYNC_STARTED, init=False
    )
    total_accounts: int = 0


class BatchSyncCompletedEvent(SyncProgressEvent):
    """Emitted when sync completes successfully."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.BATCH_SYNC_COMPLETED, init=False
    )
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    accounts_synced: int = 0


class SyncResultEvent(SyncProgressEvent):
    """Terminal result event: emitted by the command as the last event."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(default=SyncEventType.RESULT, init=False)
    success: bool = False
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    accounts_synced: int = 0


class BatchSyncFailedEvent(SyncProgressEvent):
    """Emitted when the entire batch sync fails."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.BATCH_SYNC_FAILED, init=False
    )
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    error_key: str = ""
