"""Helpers for testing streaming sync commands."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, TypeVar
from unittest.mock import AsyncMock

from swen.application.dtos.integration import BatchSyncResult, SyncResult

ResultT = TypeVar("ResultT")
ImportResultNormalizer = Callable[[object], object]


def normalize_import_result(result: object) -> object:
    data = vars(result).copy()
    data.setdefault("accounting_transaction", None)
    data.setdefault("bank_transaction", SimpleNamespace(purpose=""))
    return SimpleNamespace(**data)


def patch_streaming_import(
    service: AsyncMock,
    *,
    normalizer: ImportResultNormalizer | None = None,
) -> None:
    """Patch ``service.import_streaming`` to yield ``(idx, total, result)`` tuples.

    Configure the results to yield by setting ``service.import_streaming.return_value``
    to a list of results before calling the patched method.  For example::

        patch_streaming_import(import_service)
        import_service.import_streaming.return_value = [result1, result2]
    """

    async def import_streaming(*args: object, **kwargs: object):  # noqa: ANN202
        results = service.import_streaming.return_value or []
        total = len(results)
        for idx, r in enumerate(results, start=1):
            yield idx, total, normalizer(r) if normalizer else r

    service.import_streaming = import_streaming


async def collect_sync_result(command: Any, **kwargs: Any) -> SyncResult:
    return await _collect_streaming_result(command, SyncResult, **kwargs)


async def collect_batch_result(command: Any, **kwargs: Any) -> BatchSyncResult:
    return await _collect_streaming_result(command, BatchSyncResult, **kwargs)


def _identity(result: object) -> object:
    return result


async def _collect_streaming_result(
    command: Any,
    result_type: type[ResultT],
    **kwargs: Any,
) -> ResultT:
    result: ResultT | None = None
    async for event in command.execute_streaming(**kwargs):
        if isinstance(event, result_type):
            result = event

    assert result is not None
    return result
