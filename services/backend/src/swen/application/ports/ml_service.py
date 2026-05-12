"""ML Service port for application layer.

This abstracts the ML service operations for training examples and
account embeddings, allowing the application layer to remain independent
of infrastructure details like HTTP clients and external API contracts.

Classification is handled separately via the domain-level
CounterAccountProposalPort.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class TransactionExample:
    """Domain representation of a transaction example for ML training."""

    user_id: UUID
    account_id: UUID
    account_number: str  # Required by ML service contract
    account_type: str  # "expense" | "income" | "equity"
    transaction_id: UUID
    purpose: str
    amount: Decimal
    counterparty_name: str | None = None
    counterparty_iban: str | None = None


@dataclass(frozen=True)
class AccountForClassification:
    """Domain representation of an account option for embedding."""

    account_id: UUID
    account_number: str
    name: str
    account_type: str  # "expense" | "income" | "equity"
    description: str | None = None


class MLServicePort(ABC):
    """Port interface for ML service operations (training + embeddings).

    Classification is handled by ``CounterAccountProposalPort`` in the
    integration domain — this port covers only example submission and
    account embedding.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the ML service is enabled."""

    @abstractmethod
    def submit_example(self, example: TransactionExample) -> None:
        """Submit a transaction example for ML training (fire-and-forget)."""

    @abstractmethod
    async def embed_accounts(
        self,
        user_id: UUID,
        accounts: list[AccountForClassification],
    ) -> bool:
        """Compute and store anchor embeddings for accounts.

        Called when accounts are created or updated.
        Returns True if successful.
        """
