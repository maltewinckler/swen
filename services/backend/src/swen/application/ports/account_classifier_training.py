"""Account classifier training port for application layer.

This abstracts feeding the counter-account classifier its training data:
labeled transaction examples and per-account anchor embeddings. It keeps
the application layer independent of infrastructure details like HTTP
clients and external API contracts.

Classification itself is handled separately via the domain-level
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


class AccountClassifierTrainingPort(ABC):
    """Port for supplying the counter-account classifier its training data.

    Classification is handled by ``CounterAccountProposalPort`` in the
    integration domain. This port covers example submission and account
    anchor embedding/deletion.
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

    @abstractmethod
    def embed_accounts_fire_and_forget(
        self,
        user_id: UUID,
        accounts: list[AccountForClassification],
    ) -> None:
        """Compute and store anchor embeddings for accounts (fire-and-forget)."""

    @abstractmethod
    def delete_account_anchor_fire_and_forget(
        self,
        user_id: UUID,
        account_id: UUID,
    ) -> None:
        """Delete the anchor embedding for an account (fire-and-forget).

        Called when an account is deactivated or deleted.
        """
