"""SQLAlchemy implementation of PasswordResetTokenRepository."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.shared.time import utc_now
from swen_identity.infrastructure.persistence.sqlalchemy.models import (
    PasswordResetTokenModel,
)
from swen_identity.repositories import (
    PasswordResetTokenData,
    PasswordResetTokenRepository,
)


class PasswordResetTokenRepositorySQLAlchemy(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        token_id = uuid4()
        model = PasswordResetTokenModel(
            id=str(token_id),
            user_id=str(user_id),
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return token_id

    async def find_valid_by_hash(self, token_hash: str) -> PasswordResetTokenData | None:
        now = utc_now()
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash,
            PasswordResetTokenModel.used_at.is_(None),
            PasswordResetTokenModel.expires_at > now,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return PasswordResetTokenData(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used_at=model.used_at,
            created_at=model.created_at,
        )

    async def mark_used(self, token_id: UUID) -> None:
        stmt = (
            update(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.id == str(token_id))
            .values(used_at=utc_now())
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def invalidate_all_for_user(self, user_id: UUID) -> None:
        now = utc_now()
        stmt = (
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == str(user_id),
                PasswordResetTokenModel.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def count_recent_for_user(self, user_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == str(user_id),
                PasswordResetTokenModel.created_at >= since,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def cleanup_expired(self) -> int:
        now = utc_now()
        stmt = delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.expires_at < now,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore
