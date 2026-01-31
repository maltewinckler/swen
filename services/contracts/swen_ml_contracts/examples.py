"""Example management and lifecycle contracts.

See PRD Section 3.2 - Store Posted Example endpoint.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Store Example (Learning from posted transactions)
# -----------------------------------------------------------------------------


class StoreExampleRequest(BaseModel):
    """Store a posted transaction as a training example.

    Called when a user posts (confirms) a transaction.
    This is the primary learning signal for the ML service.
    """

    transaction_id: UUID
    counterparty_name: str | None = None
    counterparty_iban: str | None = None
    purpose: str = Field(..., min_length=1)
    amount: Decimal
    account_id: UUID
    account_number: str


class StoreExampleResponse(BaseModel):
    """Response after storing an example."""

    stored: bool
    total_examples: int
    message: str


# -----------------------------------------------------------------------------
# User Statistics
# -----------------------------------------------------------------------------


class UserStatsResponse(BaseModel):
    """Statistics about a user's training data."""

    user_id: UUID
    total_examples: int
    examples_per_account: dict[str, int]
    accounts_with_examples: int
    storage_bytes: int


# -----------------------------------------------------------------------------
# Cleanup Operations
# -----------------------------------------------------------------------------


class DeleteAccountResponse(BaseModel):
    """Response after deleting examples for an account."""

    deleted: bool
    examples_deleted: int
    message: str


class DeleteUserResponse(BaseModel):
    """Response after deleting all data for a user."""

    deleted: bool
    examples_deleted: int
    noise_model_deleted: bool
    message: str


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Service health status."""

    status: str = "ok"
    version: str

    # Model status
    embedding_model_loaded: bool
    embedding_model_name: str

    # Cache stats
    users_cached: int = 0
