"""Anchor embedding domain model."""

from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, field_validator


class Anchor(BaseModel):
    """Account anchor embedding for cold-start classification."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    account_id: UUID
    account_number: str
    name: str
    embedding: NDArray[np.float32]

    @field_validator("embedding", mode="before")
    @classmethod
    def parse_embedding(cls, v: bytes | NDArray[np.float32]) -> NDArray[np.float32]:
        """Convert bytes to numpy array if needed."""
        if isinstance(v, bytes):
            return np.frombuffer(v, dtype=np.float32)
        return v

    def embedding_bytes(self) -> bytes:
        """Serialize embedding to bytes for storage."""
        return self.embedding.astype(np.float32).tobytes()
