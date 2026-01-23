"""ML Service port for application layer.

This abstracts the ML service operations, allowing the application layer
to remain independent of infrastructure details like HTTP clients and
external API contracts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import AsyncIterator
from uuid import UUID


@dataclass(frozen=True)
class TransactionExample:
    """Domain representation of a transaction example for ML training."""

    user_id: UUID
    account_id: UUID
    account_number: str  # Required by ML service contract
    transaction_id: UUID
    purpose: str
    amount: Decimal
    counterparty_name: str | None = None
    counterparty_iban: str | None = None


@dataclass(frozen=True)
class TransactionForClassification:
    """Domain representation of a transaction to be classified."""

    transaction_id: UUID
    booking_date: date
    counterparty_name: str | None
    counterparty_iban: str | None
    purpose: str
    amount: Decimal


@dataclass(frozen=True)
class AccountForClassification:
    """Domain representation of an account option for classification."""

    account_id: UUID
    account_number: str
    name: str
    account_type: str  # "expense" | "income" | "equity"
    description: str | None = None


@dataclass(frozen=True)
class ClassificationResult:
    """Result of ML classification for a single transaction."""

    transaction_id: UUID
    account_id: UUID
    account_number: str
    confidence: float
    tier: str  # "pattern" | "example" | "anchor" | "nli" | "fallback"
    merchant: str | None = None
    is_recurring: bool = False
    recurring_pattern: str | None = None  # "monthly" | "weekly"


@dataclass(frozen=True)
class ClassificationProgress:
    """Progress update during batch classification."""

    current: int
    total: int
    last_tier: str | None = None
    last_merchant: str | None = None


@dataclass(frozen=True)
class BatchClassificationResult:
    """Result of batch ML classification."""

    classifications: list[ClassificationResult]
    processing_time_ms: int
    # Statistics
    total: int
    by_tier: dict[str, int]
    recurring_detected: int
    merchants_extracted: int


class MLServicePort(ABC):
    """Port interface for ML service operations.

    This abstraction allows application commands to interact with the ML
    service without depending on infrastructure details.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the ML service is enabled."""

    @abstractmethod
    def submit_example(self, example: TransactionExample) -> None:
        """Submit a transaction example for ML training (fire-and-forget)."""

    @abstractmethod
    async def classify_batch(
        self,
        user_id: UUID,
        transactions: list[TransactionForClassification],
        accounts: list[AccountForClassification],
    ) -> BatchClassificationResult | None:
        """Classify a batch of transactions.

        Returns None if classification fails or service is unavailable.
        """

    @abstractmethod
    async def classify_batch_streaming(
        self,
        user_id: UUID,
        transactions: list[TransactionForClassification],
        accounts: list[AccountForClassification],
    ) -> AsyncIterator[ClassificationProgress | BatchClassificationResult]:
        """Classify a batch with streaming progress updates.

        Yields ClassificationProgress during processing,
        then yields final BatchClassificationResult.
        """
        # This is an async generator - implementation uses `yield`
        ...

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
