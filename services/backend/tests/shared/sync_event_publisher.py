"""In-memory `SyncEventPublisher` test double.

Captures published events, the terminal result, and the closed flag for
unit-test assertions. Structurally implements the
`swen.application.ports.integration.SyncEventPublisher` Protocol.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"In-memory test implementation".
"""

from __future__ import annotations

from typing import Optional

from swen.application.dtos.integration import (
    BatchSyncResult,
    SyncProgressEvent,
)


class InMemorySyncEventPublisher:
    """Test double that records every published event in memory."""

    def __init__(self) -> None:
        self.events: list[SyncProgressEvent] = []
        self.terminal: Optional[BatchSyncResult] = None
        self.closed: bool = False

    async def publish(self, event: SyncProgressEvent) -> None:
        self.events.append(event)

    async def publish_terminal(self, result: BatchSyncResult) -> None:
        self.terminal = result

    async def close(self) -> None:
        self.closed = True
