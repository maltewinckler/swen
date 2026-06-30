"""Imported transaction schemas for API request/response models.

Schemas for transaction import history records.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportedTransactionResponse(BaseModel):
    """Response schema for a transaction import record."""

    id: UUID
    bank_transaction_id: UUID
    status: str
    error_message: Optional[str] = None
    transaction_id: Optional[UUID] = None
    created_at: datetime
    imported_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "bank_transaction_id": "770e8400-e29b-41d4-a716-446655440002",
                "status": "success",
                "error_message": None,
                "transaction_id": "660e8400-e29b-41d4-a716-446655440001",
                "created_at": "2024-12-05T15:00:00Z",
                "imported_at": "2024-12-05T15:00:01Z",
            },
        },
    )


class ImportedTransactionsListResponse(BaseModel):
    """Response for listing import records."""

    imports: list[ImportedTransactionResponse]
    count: int
    status_counts: dict[str, int]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "imports": [],
                "count": 0,
                "status_counts": {
                    "success": 0,
                    "failed": 0,
                    "pending": 0,
                    "duplicate": 0,
                    "skipped": 0,
                },
            },
        },
    )
