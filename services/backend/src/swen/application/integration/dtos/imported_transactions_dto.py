"""DTOs for imported transaction data transfer."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportedTransactionDTO(BaseModel):
    """DTO for a single imported transaction record.

    This is the application-layer DTO that carries import record data
    from the query layer to the presentation layer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bank_transaction_id: UUID
    status: str
    error_message: Optional[str] = None
    transaction_id: Optional[UUID] = None
    created_at: datetime
    imported_at: Optional[datetime] = None


class ImportedTransactionsListDTO(BaseModel):
    """DTO for a list of imported transaction records.

    This is the application-layer DTO that carries a list of import records
    with status counts from the query layer to the presentation layer.
    """

    model_config = ConfigDict(from_attributes=True)

    imports: list[ImportedTransactionDTO]
    count: int
    status_counts: dict[str, int]
