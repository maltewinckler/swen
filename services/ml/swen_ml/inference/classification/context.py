from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from swen_ml_contracts import TransactionInput

from swen_ml.storage.protocols import EmbeddingRepository

if TYPE_CHECKING:
    from swen_ml.inference._models import Encoder
    from swen_ml.inference.classification.enrichment.service import EnrichmentService
    from swen_ml.inference.classification.preprocessing.text_cleaner import NoiseModel
    from swen_ml.inference.shared import SharedInfrastructure
    from swen_ml.storage import RepositoryFactory


@dataclass
class EmbeddingStore:
    """In-memory embedding store for classification."""

    embeddings: NDArray[np.float32]
    account_ids: list[str]
    account_numbers: list[str]
    labels: list[str]

    def __len__(self) -> int:
        return len(self.account_ids)

    @classmethod
    def empty(cls) -> EmbeddingStore:
        return cls(
            embeddings=np.empty((0, 0), dtype=np.float32),
            account_ids=[],
            account_numbers=[],
            labels=[],
        )

    @classmethod
    async def from_repository(cls, repo: EmbeddingRepository) -> EmbeddingStore:
        """Load embeddings from any repository implementing EmbeddingRepository."""
        (
            embeddings,
            account_ids,
            account_numbers,
            labels,
        ) = await repo.get_embeddings_matrix()
        return cls(
            embeddings=embeddings,
            account_ids=account_ids,
            account_numbers=account_numbers,
            labels=labels,
        )


@dataclass
class ClassificationMatch:
    """A classification candidate from a classifier."""

    account_id: str
    account_number: str
    confidence: float


@dataclass
class TransactionContext:
    """Transaction flowing through the classification pipeline."""

    # === Original (immutable) ===
    transaction_id: UUID
    raw_counterparty: str | None
    raw_purpose: str
    amount: Decimal
    booking_date: date

    # === Step 1: Preprocessing ===
    cleaned_counterparty: str | None = None
    cleaned_purpose: str | None = None
    matched_keywords: list[str] = field(default_factory=list)

    # === Step 2: Example Classifier ===
    embedding: NDArray[np.float32] | None = None
    example_match: ClassificationMatch | None = None

    # === Step 3: Online Enrichment ===
    search_enrichment: str | None = None

    # === Step 4: Anchor Classifier ===
    enriched_embedding: NDArray[np.float32] | None = None
    anchor_match: ClassificationMatch | None = None

    # === Resolution ===
    resolved: bool = False
    resolved_by: str | None = None  # "example" | "anchor" | None

    @classmethod
    def from_input(cls, txn: TransactionInput) -> TransactionContext:
        return cls(
            transaction_id=txn.transaction_id,
            raw_counterparty=txn.counterparty_name,
            raw_purpose=txn.purpose,
            amount=txn.amount,
            booking_date=txn.booking_date,
        )

    def get_classification(self) -> ClassificationMatch | None:
        if self.resolved_by == "example":
            return self.example_match
        if self.resolved_by == "anchor":
            return self.anchor_match
        return None


@dataclass
class PipelineContext:
    """Shared resources for all pipeline components."""

    encoder: Encoder
    noise_model: NoiseModel
    example_store: EmbeddingStore
    anchor_store: EmbeddingStore
    enrichment_service: EnrichmentService | None = None
    confidence_threshold: float = 0.85

    @classmethod
    async def from_repositories(
        cls,
        infra: SharedInfrastructure,
        repos: RepositoryFactory,
    ) -> PipelineContext:
        """Load user-specific data from repositories."""
        from swen_ml.inference.classification.preprocessing.text_cleaner import (
            NoiseModel,
        )

        noise_model = await NoiseModel.from_repository(repos.noise)
        example_store = await EmbeddingStore.from_repository(repos.example)
        anchor_store = await EmbeddingStore.from_repository(repos.anchor)

        return cls(
            encoder=infra.encoder,
            noise_model=noise_model,
            example_store=example_store,
            anchor_store=anchor_store,
            enrichment_service=infra.enrichment_service,
            confidence_threshold=infra.settings.example_high_confidence,
        )
