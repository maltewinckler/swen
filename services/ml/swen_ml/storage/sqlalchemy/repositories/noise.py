from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swen_ml.data_models import NoiseData
from swen_ml.storage.sqlalchemy.tables import NoiseTable


class NoiseRepository:
    """Repository for user noise models (IDF weights)."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self._session = session
        self._user_id = user_id

    async def save(
        self,
        token_frequencies: dict[str, int],
        document_count: int,
    ):
        """Save or update the user's noise model."""
        stmt = insert(NoiseTable).values(
            user_id=self._user_id,
            token_frequencies=token_frequencies,
            document_count=document_count,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "token_frequencies": token_frequencies,
                "document_count": document_count,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get(self) -> NoiseData | None:
        """Get the user's noise model."""
        stmt = select(NoiseTable).where(NoiseTable.user_id == self._user_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return NoiseData(
            token_frequencies=row.token_frequencies,
            document_count=row.document_count,
        )
