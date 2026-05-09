"""ML Service adapter implementing the application port.

Handles example submission and account embeddings. Classification is
handled separately by ``MLCounterAccountAdapter``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen_ml_contracts import AccountOption, StoreExampleRequest

from swen.application.ports.ml_service import (
    AccountForClassification,
    MLServicePort,
    TransactionExample,
)

if TYPE_CHECKING:
    from uuid import UUID

    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class MLServiceAdapter(MLServicePort):
    """Infrastructure adapter that implements MLServicePort.

    Translates domain objects to ML contracts and delegates to the HTTP client.
    Covers example submission and account embeddings only.
    """

    def __init__(self, client: MLServiceClient):
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    def submit_example(self, example: TransactionExample) -> None:
        """Submit a posted transaction as a training example (fire-and-forget)."""
        if not self._client.enabled:
            return

        request = StoreExampleRequest(
            transaction_id=example.transaction_id,
            counterparty_name=example.counterparty_name,
            counterparty_iban=example.counterparty_iban,
            purpose=example.purpose,
            amount=example.amount,
            account_id=example.account_id,
            account_number=example.account_number,
            account_type=example.account_type,
        )

        self._client.store_example_fire_and_forget(example.user_id, request)
        logger.debug(
            "Submitted ML example: txn=%s -> account=%s",
            example.transaction_id,
            example.account_number,
        )

    async def embed_accounts(
        self,
        user_id: UUID,
        accounts: list[AccountForClassification],
    ) -> bool:
        """Compute and store anchor embeddings for accounts."""
        if not self._client.enabled:
            return False

        ml_accounts = [
            AccountOption(
                account_id=acc.account_id,
                account_number=acc.account_number,
                name=acc.name,
                account_type=acc.account_type,
                description=acc.description,
            )
            for acc in accounts
        ]

        result = await self._client.embed_accounts(user_id, ml_accounts)
        return result is not None and result.embedded > 0
