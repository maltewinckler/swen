"""Unit tests for `SseSyncEventPublisher`."""

from __future__ import annotations

import asyncio

import pytest

from swen.application.events import BatchSyncStartedEvent, SyncProgressEvent
from swen.application.ports.integration import SyncEventPublisher
from swen.infrastructure.integration.adapters.event_publisher import (
    SseSyncEventPublisher,
)


def test_satisfies_sync_event_publisher_protocol() -> None:
    """The publisher structurally implements the application port."""
    pub: SyncEventPublisher = SseSyncEventPublisher()
    assert pub is not None


async def test_events_yields_published_items_in_order() -> None:
    pub = SseSyncEventPublisher()

    first = BatchSyncStartedEvent(total_accounts=2)
    second = BatchSyncStartedEvent(total_accounts=3)

    await pub.publish(first)
    await pub.publish(second)
    await pub.close()

    received: list[SyncProgressEvent] = []
    async for item in pub.events():
        received.append(item)

    assert received == [first, second]


async def test_close_terminates_iterator_without_yielding_sentinel() -> None:
    pub = SseSyncEventPublisher()
    await pub.close()

    received: list[object] = []
    async for item in pub.events():
        received.append(item)

    assert received == []


async def test_concurrent_producer_and_consumer() -> None:
    pub = SseSyncEventPublisher()
    started = BatchSyncStartedEvent(total_accounts=1)

    async def produce() -> None:
        await pub.publish(started)
        await pub.close()

    received: list[SyncProgressEvent] = []

    async def consume() -> None:
        async for item in pub.events():
            received.append(item)

    await asyncio.gather(produce(), consume())

    assert len(received) == 1
    assert received[0] is started


@pytest.mark.parametrize("count", [0, 1, 5])
async def test_publish_count_matches_received_count(count: int) -> None:
    pub = SseSyncEventPublisher()

    for _ in range(count):
        await pub.publish(BatchSyncStartedEvent(total_accounts=0))
    await pub.close()

    received: list[SyncProgressEvent] = []
    async for item in pub.events():
        received.append(item)

    assert len(received) == count
