"""Account anchor embedding contracts.

See PRD Section 4.3 - Tier 3: Anchor Retrieval.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from swen_ml_contracts.common import AccountOption


class EmbedAccountsRequest(BaseModel):
    """Request to compute and store account anchor embeddings.

    Called when a user creates accounts or updates account descriptions.
    Anchors are used for cold-start classification when no examples exist.
    """

    user_id: UUID
    accounts: list[AccountOption] = Field(default_factory=list)


class EmbedAccountsResponse(BaseModel):
    """Response after embedding accounts."""

    embedded: int
    message: str
