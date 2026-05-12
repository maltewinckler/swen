"""SQLAlchemy implementation of the UnitOfWork port."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWorkSQLAlchemy:
    """Wraps an AsyncSession: commits on clean exit, rolls back on exception."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> "UnitOfWorkSQLAlchemy":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()
