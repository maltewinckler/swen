"""ML-backed implementation of AccountClassifierTrainingPort.

Handles example submission and account embeddings. Classification is
handled separately by ``MLCounterAccountAdapter``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen_ml_contracts import AccountOption, StoreExampleRequest

from swen.application.ports.account_classifier_training import (
    AccountClassifierTrainingPort,
    AccountForClassification,
    TransactionExample,
)

if TYPE_CHECKING:
    from uuid import UUID

    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class MLAccountClassifierTrainingAdapter(AccountClassifierTrainingPort):
    """Infrastructure adapter that implements AccountClassifierTrainingPort.

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

        ml_accounts = [AccountOption.model_validate(acc) for acc in accounts]

        result = await self._client.embed_accounts(user_id, ml_accounts)
        return result is not None and result.embedded > 0

    def embed_accounts_fire_and_forget(
        self,
        user_id: UUID,
        accounts: list[AccountForClassification],
    ) -> None:
        """Compute and store anchor embeddings for accounts (fire-and-forget)."""
        if not self._client.enabled:
            return

        ml_accounts = [AccountOption.model_validate(acc) for acc in accounts]

        self._client.embed_accounts_fire_and_forget(user_id, ml_accounts)

    def delete_account_anchor_fire_and_forget(
        self,
        user_id: UUID,
        account_id: UUID,
    ) -> None:
        """Delete the anchor embedding for an account (fire-and-forget)."""
        if not self._client.enabled:
            return

        self._client.delete_account_anchor_fire_and_forget(user_id, account_id)
