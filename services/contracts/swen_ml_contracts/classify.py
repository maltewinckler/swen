"""Classification request/response models.

See PRD Section 3.2 for API contract details.
"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    """Transaction data for classification."""

    transaction_id: UUID
    booking_date: date
    counterparty_name: str | None = None
    counterparty_iban: str | None = None
    purpose: str = Field(..., min_length=1)
    amount: Decimal


class ClassifyBatchRequest(BaseModel):
    """Batch classification request.

    All classification goes through the batch endpoint.
    For single transactions, send a batch of one.
    """

    user_id: UUID
    transactions: list[TransactionInput] = Field(..., min_length=1)


ClassificationTier = Literal["example", "anchor", "unresolved"]


class Classification(BaseModel):
    """Classification result for a single transaction.

    account_id and account_number are None if unresolved.
    Backend is responsible for applying fallback logic.
    """

    transaction_id: UUID
    account_id: UUID | None = None
    account_number: str | None = None

    confidence: float = Field(..., ge=0.0, le=1.0)
    tier: ClassificationTier

    # Merchant extraction (PRD Section 2.4)
    merchant: str | None = None

    # Recurring pattern detection (PRD Section 4.5)
    is_recurring: bool = False
    recurring_pattern: Literal["monthly", "weekly"] | None = None


class ClassificationStats(BaseModel):
    """Statistics about the batch classification."""

    total: int

    by_tier: dict[ClassificationTier, int] = Field(default_factory=dict)
    by_confidence: dict[Literal["high", "medium", "low"], int] = Field(
        default_factory=dict
    )

    recurring_detected: int = 0
    merchants_extracted: int = 0


class ClassifyBatchResponse(BaseModel):
    """Batch classification response."""

    classifications: list[Classification]
    stats: ClassificationStats
    processing_time_ms: int = Field(..., ge=0)
