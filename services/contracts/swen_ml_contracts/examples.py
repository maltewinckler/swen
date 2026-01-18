"""Example management and lifecycle contracts."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import AccountOption


class AddExampleRequest(BaseModel):
    """Add a posted transaction as a classification example."""

    user_id: UUID
    account_id: UUID
    purpose: str = Field(..., min_length=1)
    amount: Decimal
    counterparty_name: str | None = None
    reference: str | None = None
    transaction_id: UUID | None = None  # for deduplication


class AddExampleResponse(BaseModel):
    stored: bool
    total_examples: int
    message: str
    constructed_text: str | None = None


class EmbedAccountsRequest(BaseModel):
    user_id: UUID
    accounts: list[AccountOption] = Field(..., min_length=1)


class EmbedAccountsResponse(BaseModel):
    embedded: int
    message: str


class UserStatsResponse(BaseModel):
    user_id: UUID
    total_examples: int
    examples_per_account: dict[str, int]
    accounts_with_examples: int
    accounts_without_examples: int
    storage_bytes: int


class DeleteAccountResponse(BaseModel):
    deleted: bool
    examples_deleted: int
    message: str


class DeleteUserResponse(BaseModel):
    deleted: bool
    accounts_deleted: int
    examples_deleted: int
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    model_loaded: bool
    model_name: str
    total_users: int = 0
