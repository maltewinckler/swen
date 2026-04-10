"""SQLAlchemy implementation of FinTSEndpointRepository."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from swen.infrastructure.banking.geldstrom.fints_endpoint_repository import (
    FinTSEndpointRepository,
)
from swen.infrastructure.persistence.sqlalchemy.models.banking.geldstrom.fints_endpoint_model import (  # noqa: E501
    FinTSEndpointModel,
)

logger = logging.getLogger(__name__)


class FinTSEndpointRepositorySQLAlchemy(FinTSEndpointRepository):
    """SQLAlchemy implementation (system-wide, not user-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_blz(self, blz: str) -> str | None:
        stmt = select(FinTSEndpointModel.endpoint_url).where(
            FinTSEndpointModel.blz == blz,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_batch(self, endpoints: dict[str, str]) -> int:
        if not endpoints:
            return 0

        values = [{"blz": blz, "endpoint_url": url} for blz, url in endpoints.items()]

        stmt = pg_insert(FinTSEndpointModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["blz"],
            set_={"endpoint_url": stmt.excluded.endpoint_url},
        )
        await self._session.execute(stmt)
        await self._session.flush()
        logger.info("Upserted %d FinTS endpoint records", len(endpoints))
        return len(endpoints)
