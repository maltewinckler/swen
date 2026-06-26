"""DTOs for account mapping data transfer."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountMappingDTO(BaseModel):
    """DTO for a single account mapping with resolved account info.

    This is the application-layer DTO that carries mapping data
    (joined with account data) from the query layer to the presentation layer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    iban: str
    account_name: str
    accounting_account_id: UUID
    accounting_account_name: Optional[str] = None
    accounting_account_number: Optional[str] = None
    created_at: Optional[str] = None


class AccountMappingListDTO(BaseModel):
    """DTO for a list of account mappings.

    This is the application-layer DTO that carries a paginated list
    of account mappings from the query layer to the presentation layer.
    """

    model_config = ConfigDict(from_attributes=True)

    mappings: list[AccountMappingDTO]
    count: int
