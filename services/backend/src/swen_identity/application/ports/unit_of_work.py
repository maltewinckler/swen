"""Unit of Work port — infrastructure-agnostic transaction boundary."""

from __future__ import annotations

from typing import Protocol


class UnitOfWork(Protocol):
    """Atomic transaction scope for a single use case.

    Usage in commands::

        async with self._uow:
            # All writes here are committed on clean exit,
            # rolled back if any exception propagates.
    """

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...
