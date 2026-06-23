"""Helpers for testing streaming sync commands."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Callable
from unittest.mock import AsyncMock

ImportResultNormalizer = Callable[[object], object]


def normalize_import_result(result: object) -> object:
    data = vars(result).copy()
    data.setdefault("accounting_transaction", None)
    data.setdefault("bank_transaction", SimpleNamespace(purpose=""))
    return SimpleNamespace(**data)


def patch_batch_import(
    service: AsyncMock,
    *,
    normalizer: ImportResultNormalizer | None = None,
) -> None:
    """Patch ``service.import_batch`` to return a list of results.

    Configure the results to return by setting ``service.import_batch.return_value``
    to a list of results before calling the patched method.  For example::

        patch_batch_import(import_service)
        import_service.import_batch.return_value = [result1, result2]
    """

    async def import_batch(*args: object, **kwargs: object) -> list:
        results = service.import_batch.return_value or []
        if normalizer:
            return [normalizer(r) for r in results]
        return list(results)

    service.import_batch = import_batch
