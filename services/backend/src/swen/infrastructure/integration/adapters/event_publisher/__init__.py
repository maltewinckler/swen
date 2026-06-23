"""Event publisher infrastructure adapters.

Concrete implementations of the application-layer
`SyncEventPublisher` Protocol live here.
"""

from swen.infrastructure.integration.adapters.event_publisher.sse_sync_event_publisher import (  # NOQA: E501
    SseSyncEventPublisher,
)

__all__ = ["SseSyncEventPublisher"]
