from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen_ml_contracts import TransactionInput

from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.integration.ports.counter_account_proposal_port import (
    CounterAccountProposalPort,
)
from swen.domain.integration.value_objects import (
    CounterAccountProposal,
)

if TYPE_CHECKING:
    from uuid import UUID

    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class MLCounterAccountAdapter(CounterAccountProposalPort):
    """Implements CounterAccountProposalPort by delegating to MLServiceClient."""

    def __init__(self, ml_client: MLServiceClient) -> None:
        self._client = ml_client

    async def classify_batch(
        self,
        user_id: UUID,
        transactions: list[StoredBankTransaction],
    ) -> list[CounterAccountProposal] | None:
        if not self._client.enabled:
            return None

        ml_transactions = [
            TransactionInput(
                transaction_id=t.id,
                booking_date=t.transaction.booking_date,
                purpose=t.transaction.purpose or "",
                amount=t.transaction.amount,
                counterparty_name=t.transaction.applicant_name,
                counterparty_iban=t.transaction.applicant_iban,
            )
            for t in transactions
        ]

        response = await self._client.classify_batch(
            user_id=user_id,
            transactions=ml_transactions,
        )
        if response is None:
            return None

        return [
            CounterAccountProposal(
                transaction_id=c.transaction_id,
                counter_account_id=c.account_id,
                confidence=c.confidence,
            )
            for c in response.classifications
        ]
