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


def wire_streaming_imports(
    service: AsyncMock,
    *,
    normalizer: ImportResultNormalizer | None = None,
) -> None:
    result_normalizer = normalizer or _identity
    service.import_from_stored_transactions = AsyncMock(return_value=[])
    service.import_with_preclassified = AsyncMock(return_value=[])

    async def import_from_stored_transactions_streaming(*args, **kwargs):
        results = await service.import_from_stored_transactions(*args, **kwargs)
        total = len(results)
        for index, result in enumerate(results, start=1):
            yield index, total, result_normalizer(result)

    async def import_with_preclassified_streaming(*args, **kwargs):
        results = await service.import_with_preclassified(*args, **kwargs)
        total = len(results)
        for index, result in enumerate(results, start=1):
            yield index, total, result_normalizer(result)

    service.import_from_stored_transactions_streaming = (
        import_from_stored_transactions_streaming
    )
    service.import_with_preclassified_streaming = import_with_preclassified_streaming


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
