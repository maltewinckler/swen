"""Counter-account proposal value object.

Represents a resolution engine's proposal for the counter-account
of a bank transaction. Carries confidence and tier metadata.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CounterAccountProposal(BaseModel):
    """A single counter-account proposal returned by the resolution engine."""

    model_config = ConfigDict(frozen=True, validate_assignment=True)

    transaction_id: UUID
    counter_account_id: UUID | None
    confidence: float
