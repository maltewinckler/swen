"""Classification request/response models.

See PRD Section 3.2 for API contract details.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from uuid import UUID

from .common import AccountOption


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------


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
    available_accounts: list[AccountOption] = Field(..., min_length=1)


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


ClassificationTier = Literal["pattern", "example", "anchor", "nli", "fallback"]


class Classification(BaseModel):
    """Classification result for a single transaction."""

    transaction_id: UUID
    account_id: UUID
    account_number: str

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
