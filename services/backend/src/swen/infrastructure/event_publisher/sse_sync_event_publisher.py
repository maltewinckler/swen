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

from swen.application.dtos.integration import (
    BatchSyncResult,
    SyncProgressEvent,
)


class SseSyncEventPublisher:
    """Queue-backed publisher that fans out events to a single consumer.

    Producers call :meth:`publish` / :meth:`publish_terminal` / :meth:`close`.
    The consumer iterates :meth:`events`, which yields published events and
    the optional terminal :class:`BatchSyncResult` until :meth:`close` puts
    the sentinel on the queue.
    """

    _SENTINEL: object = object()

    def __init__(self) -> None:
        self._queue: asyncio.Queue[SyncProgressEvent | BatchSyncResult | object] = (
            asyncio.Queue()
        )

    async def publish(self, event: SyncProgressEvent) -> None:
        """Publish a progress event."""
        await self._queue.put(event)

    async def publish_terminal(self, result: BatchSyncResult) -> None:
        """Publish the final result. After this, no more events are accepted."""
        await self._queue.put(result)

    async def close(self) -> None:
        """Signal the consumer that the stream is done."""
        await self._queue.put(self._SENTINEL)

    async def events(
        self,
    ) -> AsyncIterator[SyncProgressEvent | BatchSyncResult]:
        """Yield published items until :meth:`close` is called."""
        while True:
            item = await self._queue.get()
            if item is self._SENTINEL:
                return
            # Narrow the union: the sentinel is the only `object` we
            # ever enqueue; everything else is `SyncProgressEvent` or
            # `BatchSyncResult`.
            yield item  # type: ignore[misc]
