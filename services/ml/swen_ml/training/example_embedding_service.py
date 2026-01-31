"""Service for creating and storing example embeddings."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from swen_ml.inference._models import Encoder
    from swen_ml.storage import ExampleRepository, RepositoryFactory

logger = logging.getLogger(__name__)


class ExampleEmbeddingService:
    """Service for managing example embeddings."""

    def __init__(self, encoder: Encoder, repository: ExampleRepository):
        self.encoder = encoder
        self.repository = repository

    @classmethod
    def from_factory(
        cls,
        encoder: Encoder,
        factory: RepositoryFactory,
    ) -> ExampleEmbeddingService:
        return cls(encoder=encoder, repository=factory.example)

    async def store_example(
        self,
        counterparty_name: str | None,
        purpose: str,
        account_id: UUID,
        account_number: str,
    ) -> int:
        parts = []
        if counterparty_name:
            parts.append(counterparty_name)
        parts.append(purpose)
        text = " ".join(parts)

        # Encode
        embedding = self.encoder.encode([text])[0]

        # Store in database
        await self.repository.add(
            embedding=embedding,
            account_id=str(account_id),
            account_number=account_number,
            text=text,
        )

        total = await self.repository.count()
        logger.info("Stored example for account=%s, total=%d", account_number, total)
        return total
