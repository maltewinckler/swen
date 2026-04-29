"""SQLAlchemy implementation of BankInfoRepository."""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.banking.repositories.bank_info_repository import BankInfoRepository
from swen.domain.banking.value_objects.bank_info import BankInfo
from swen.infrastructure.persistence.sqlalchemy.models.banking.bank_info_model import (
    BankInfoModel,
)

logger = logging.getLogger(__name__)


class BankInfoRepositorySQLAlchemy(BankInfoRepository):
    """SQLAlchemy implementation (system-wide, not user-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_blz(self, blz: str) -> BankInfo | None:
        stmt = select(BankInfoModel).where(BankInfoModel.blz == blz)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all(self) -> list[BankInfo]:
        stmt = select(BankInfoModel).order_by(BankInfoModel.name)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def save_batch(
        self,
        banks: list[BankInfo],
        source: Literal["csv", "api"],
    ) -> int:
        if not banks:
            return 0

        values = [
            {
                "blz": b.blz,
                "name": b.name,
                "bic": b.bic,
                "organization": b.organization,
                "is_fints_capable": b.is_fints_capable,
                "source": source,
            }
            for b in banks
        ]

        stmt = pg_insert(BankInfoModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["blz"],
            set_={
                "name": stmt.excluded.name,
                "bic": stmt.excluded.bic,
                "organization": stmt.excluded.organization,
                "is_fints_capable": stmt.excluded.is_fints_capable,
                "source": stmt.excluded.source,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        logger.info(
            "Upserted %d bank information records (source=%s)", len(banks), source
        )
        return len(banks)

    async def count(self) -> int:
        stmt = select(func.count()).select_from(BankInfoModel)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: BankInfoModel) -> BankInfo:
        return BankInfo(
            blz=model.blz,
            name=model.name,
            bic=model.bic,
            organization=model.organization,
            is_fints_capable=model.is_fints_capable,
        )
