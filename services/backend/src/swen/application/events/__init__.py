"""Application-layer events.

Streaming progress events published through SyncEventPublisher (SSE).
Split by concern:
- base: SyncProgressEvent base class, SyncEventType enum, ErrorCode enum
- account_sync_events: per-account sync lifecycle events
- batch_sync_events: batch sync lifecycle events
- classification_events: ML classification progress events
"""

from swen.application.events.account_sync_events import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
)
from swen.application.events.base import (
    ErrorCode,
    SyncEventType,
    SyncProgressEvent,
)
from swen.application.events.batch_sync_events import (
    BatchSyncCompletedEvent,
    BatchSyncFailedEvent,
    BatchSyncStartedEvent,
    SyncResultEvent,
)
from swen.application.events.classification_events import (
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
)

__all__ = [
    "AccountSyncCompletedEvent",
    "AccountSyncFailedEvent",
    "AccountSyncFetchedEvent",
    "AccountSyncStartedEvent",
    "BatchSyncCompletedEvent",
    "BatchSyncFailedEvent",
    "BatchSyncStartedEvent",
    "ClassificationCompletedEvent",
    "ClassificationProgressEvent",
    "ClassificationStartedEvent",
    "ErrorCode",
    "SyncEventType",
    "SyncProgressEvent",
    "SyncResultEvent",
]
