"""Port for batch counter-account proposal generation.

Decouples the domain from any particular resolution engine
(ML model, etc.). The implementation lives in infrastructure.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from swen.domain.banking.repositories import StoredBankTransaction
from swen.domain.integration.value_objects import (
    CounterAccountProposal,
)


class CounterAccountProposalPort(Protocol):
    """Port: submit a batch of transactions and receive counter-account proposals.

    Any resolution engine (ML service, etc.) satisfies this contract by
    implementing :meth:`classify_batch`.
    """

    async def classify_batch(
        self,
        user_id: UUID,
        transactions: list[StoredBankTransaction],
    ) -> list[CounterAccountProposal] | None:
        """Classify a batch of transactions.

        Returns a list of proposals in the same order as ``transactions``,
        or ``None`` if the classifier is unavailable.
        """
        ...
