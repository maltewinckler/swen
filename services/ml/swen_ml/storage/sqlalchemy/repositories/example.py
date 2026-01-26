from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen_ml.data_models import Example
from swen_ml.storage.sqlalchemy.tables import ExampleTable


class ExampleRepository:
    """Repository for user training examples."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self._session = session
        self._user_id = user_id

    async def add(
        self,
        embedding: NDArray[np.float32],
        account_id: str,
        account_number: str,
        text: str,
    ):
        """Add a new training example."""
        example = ExampleTable(
            user_id=self._user_id,
            embedding=embedding.astype(np.float32).tobytes(),
            account_id=account_id,
            account_number=account_number,
            text=text,
        )
        self._session.add(example)
        await self._session.commit()

    async def get_all(self) -> list[Example]:
        """Get all training examples for the user."""
        stmt = select(ExampleTable).where(ExampleTable.user_id == self._user_id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            Example(
                account_id=row.account_id,
                account_number=row.account_number,
                text=row.text,
                embedding=np.frombuffer(row.embedding, dtype=np.float32),
            )
            for row in rows
        ]

    async def get_embeddings_matrix(
        self,
    ) -> tuple[NDArray[np.float32], list[str], list[str], list[str]]:
        """Get all examples as a numpy matrix for efficient similarity computation.

        Returns:
            Tuple of (embeddings_matrix, account_ids, account_numbers, texts)
        """
        examples = await self.get_all()

        if not examples:
            return np.empty((0, 0), dtype=np.float32), [], [], []

        embeddings = np.vstack([e.embedding for e in examples])
        account_ids = [e.account_id for e in examples]
        account_numbers = [e.account_number for e in examples]
        texts = [e.text for e in examples]

        return embeddings, account_ids, account_numbers, texts

    async def count(self) -> int:
        """Count examples for the user."""
        stmt = (
            select(func.count())
            .select_from(ExampleTable)
            .where(ExampleTable.user_id == self._user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
