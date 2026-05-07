"""Event publisher infrastructure adapters.

Concrete implementations of the application-layer
`SyncEventPublisher` Protocol live here.
"""

from swen.infrastructure.event_publisher.sse_sync_event_publisher import (
    SseSyncEventPublisher,
)

__all__ = ["SseSyncEventPublisher"]
