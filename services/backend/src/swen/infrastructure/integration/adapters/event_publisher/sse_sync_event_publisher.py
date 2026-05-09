"""SSE-oriented `SyncEventPublisher` implementation.

Backed by an `asyncio.Queue` with a `_SENTINEL` close marker. The class
is a pure queue-fan-out: it knows nothing about FastAPI, SSE framing, or
HTTP. The router consumes published items via the `events()` async
iterator and is responsible for SSE formatting.

Structurally implements the
`swen.application.ports.integration.SyncEventPublisher` Protocol.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"SSE implementation".
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from swen.application.events.base import SyncProgressEvent
from swen.application.ports.integration.sync_event_publisher import SyncEventPublisher


class SseSyncEventPublisher(SyncEventPublisher):
    """Queue-backed publisher that fans out events to a single consumer.

    Producers call :meth:`publish` / :meth:`close`.
    The consumer iterates :meth:`events`, which yields progress events until
    :meth:`close` puts the sentinel on the queue.
    """

    _SENTINEL: object = object()

    def __init__(self) -> None:
        self._queue: asyncio.Queue[SyncProgressEvent | object] = asyncio.Queue()

    async def publish(self, event: SyncProgressEvent) -> None:
        """Publish a progress event."""
        await self._queue.put(event)

    async def close(self) -> None:
        """Signal the consumer that the stream is done."""
        await self._queue.put(self._SENTINEL)

    async def events(self) -> AsyncIterator[SyncProgressEvent]:
        """Yield progress events until :meth:`close` is called."""
        while True:
            item = await self._queue.get()
            if item is self._SENTINEL:
                return
            yield item  # type: ignore[misc]
