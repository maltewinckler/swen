"""Service for creating and storing account anchor embeddings."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen_ml_contracts import AccountOption

if TYPE_CHECKING:
    from swen_ml.inference._models import Encoder
    from swen_ml.storage import AnchorRepository, RepositoryFactory

logger = logging.getLogger(__name__)


class AccountEmbeddingService:
    """Service for managing account anchor embeddings."""

    def __init__(self, encoder: Encoder, repository: AnchorRepository):
        self.encoder = encoder
        self.repository = repository

    @classmethod
    def from_factory(
        cls,
        encoder: Encoder,
        factory: RepositoryFactory,
    ) -> AccountEmbeddingService:
        return cls(encoder=encoder, repository=factory.anchor)

    async def embed_accounts(self, accounts: list[AccountOption]) -> int:
        if not accounts:
            return 0

        embedded_count = 0
        for account in accounts:
            # Build text from account name + description
            text = account.name
            if account.description:
                text = f"{account.name}: {account.description}"

            # Encode
            embedding = self.encoder.encode([text])[0]

            # Upsert into database
            await self.repository.upsert(
                account_id=account.account_id,
                embedding=embedding,
                account_number=account.account_number,
                name=account.name,
            )
            embedded_count += 1

        logger.info("Embedded %d account anchors", embedded_count)

        return embedded_count

    async def delete_account(self, account_id: UUID) -> bool:
        deleted = await self.repository.delete(account_id)

        if deleted:
            logger.info("Deleted anchor for account=%s", account_id)
        else:
            logger.debug("No anchor found to delete for account=%s", account_id)

        return deleted

    async def delete_all(self) -> int:
        count = await self.repository.delete_all()

        if count > 0:
            logger.info("Deleted %d anchors", count)
        else:
            logger.debug("No anchors found")

        return count
