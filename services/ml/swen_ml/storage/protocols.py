"""Storage layer protocols."""

from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class EmbeddingRepository(Protocol):
    """Protocol for repositories that provide embedding matrices."""

    async def get_embeddings_matrix(
        self,
    ) -> tuple[NDArray[np.float32], list[str], list[str], list[str]]:
        """Return (embeddings, account_ids, account_numbers, labels)."""
        ...
