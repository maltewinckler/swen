"""Shared models for ML service contracts."""

from uuid import UUID

from pydantic import BaseModel, Field


class AccountOption(BaseModel):
    """Account available for classification."""

    account_id: UUID
    account_number: str = Field(..., max_length=10)
    name: str = Field(..., max_length=100)
    account_type: str = Field(..., pattern="^(expense|income)$")
    description: str | None = Field(None, max_length=500)
