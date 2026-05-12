"""Sync event publisher port.

Application services publish sync progress events as side effects through
this port. The implementation decides what "delivery" means (SSE queue,
in-memory buffer for tests, no-op, structured log, ...).

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"`SyncEventPublisher` port".
"""

from __future__ import annotations

from typing import Protocol

from swen.application.events.base import SyncProgressEvent


class SyncEventPublisher(Protocol):
    """Sink for sync progress events.

    Application services publish events as side effects. The implementation
    decides what 'delivery' means (SSE queue, in-memory buffer for tests,
    no-op, structured log, ...).
    """

    async def publish(self, event: SyncProgressEvent) -> None:
        """Publish a progress event."""
        ...

    async def close(self) -> None:
        """Signal the consumer that the stream is done."""
        ...
