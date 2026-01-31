from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swen_ml.data_models import Anchor
from swen_ml.storage.sqlalchemy.tables import AnchorTable


class AnchorRepository:
    """Repository for account anchor embeddings."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self._session = session
        self._user_id = user_id

    async def upsert(
        self,
        account_id: UUID,
        embedding: NDArray[np.float32],
        account_number: str,
        name: str,
    ):
        """Insert or update a single anchor embedding."""
        embedding_bytes = embedding.astype(np.float32).tobytes()

        stmt = insert(AnchorTable).values(
            user_id=self._user_id,
            account_id=account_id,
            embedding=embedding_bytes,
            account_number=account_number,
            name=name,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "account_id"],
            set_={
                "embedding": embedding_bytes,
                "account_number": account_number,
                "name": name,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def delete(self, account_id: UUID) -> bool:
        """Delete a single anchor embedding. Returns True if deleted."""
        stmt = delete(AnchorTable).where(
            AnchorTable.user_id == self._user_id,
            AnchorTable.account_id == account_id,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return (result.rowcount or 0) > 0  # type: ignore[union-attr]

    async def delete_all(self) -> int:
        """Delete all anchors for the user. Returns count of deleted."""
        stmt = delete(AnchorTable).where(AnchorTable.user_id == self._user_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0  # type: ignore[union-attr, return-value]

    async def get_all(self) -> list[Anchor]:
        """Get all anchor embeddings for the user."""
        stmt = select(AnchorTable).where(AnchorTable.user_id == self._user_id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            Anchor(
                account_id=row.account_id,
                account_number=row.account_number,
                name=row.name,
                embedding=np.frombuffer(row.embedding, dtype=np.float32),
            )
            for row in rows
        ]

    async def get_embeddings_matrix(
        self,
    ) -> tuple[NDArray[np.float32], list[str], list[str], list[str]]:
        """Get all anchors as a numpy matrix for efficient similarity computation.

        Returns:
            Tuple of (embeddings_matrix, account_ids, account_numbers, names)
        """
        anchors = await self.get_all()

        if not anchors:
            return np.empty((0, 0), dtype=np.float32), [], [], []

        embeddings = np.vstack([a.embedding for a in anchors])
        account_ids = [str(a.account_id) for a in anchors]
        account_numbers = [a.account_number for a in anchors]
        names = [a.name for a in anchors]

        return embeddings, account_ids, account_numbers, names
