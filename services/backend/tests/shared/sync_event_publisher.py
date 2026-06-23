"""In-memory `SyncEventPublisher` test double.

Captures published events, the terminal result, and the closed flag for
unit-test assertions. Structurally implements the
`swen.application.ports.integration.SyncEventPublisher` Protocol.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"In-memory test implementation".
"""

from __future__ import annotations

from swen.application.events.base import SyncProgressEvent


class InMemorySyncEventPublisher:
    """Test double that records every published event in memory."""

    def __init__(self) -> None:
        self.events: list[SyncProgressEvent] = []
        self.closed: bool = False

    async def publish(self, event: SyncProgressEvent) -> None:
        self.events.append(event)

    async def close(self) -> None:
        self.closed = True
