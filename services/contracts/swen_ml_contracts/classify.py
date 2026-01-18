"""Classification request/response models."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import AccountOption


class TransactionInput(BaseModel):
    """Transaction data for classification."""

    booking_date: date
    purpose: str = Field(..., min_length=1)
    amount: Decimal
    counterparty_name: str | None = None
    counterparty_iban: str | None = None
    reference: str | None = None


class ClassifyRequest(BaseModel):
    user_id: UUID
    transaction: TransactionInput
    available_accounts: list[AccountOption] = Field(..., min_length=1)


class ClassifyBatchRequest(BaseModel):
    user_id: UUID
    transactions: list[TransactionInput] = Field(..., min_length=1, max_length=1000)
    available_accounts: list[AccountOption] = Field(..., min_length=1)


class ClassificationResult(BaseModel):
    """Result of similarity-based classification."""

    account_id: UUID | None = None
    account_number: str | None = None

    similarity_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    margin_over_second: float = Field(0.0, ge=0.0)

    match_type: Literal["example", "description"] | None = None
    matched_text: str | None = None
    reasoning: str | None = None

    @property
    def has_prediction(self) -> bool:
        return self.account_id is not None


class ClassifyResponse(ClassificationResult):
    inference_time_ms: int = Field(..., ge=0)


class ClassifyBatchResponse(BaseModel):
    results: list[ClassificationResult]
    total_inference_time_ms: int = Field(..., ge=0)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.has_prediction)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.success_count / len(self.results)
