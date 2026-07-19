"""Imported transaction schemas for API request/response models.

Schemas for transaction import history records.
"""

from pydantic import ConfigDict

from swen.application.integration.dtos import ImportedTransactionsListDTO


class ImportedTransactionsListResponse(ImportedTransactionsListDTO):
    """Response for listing import records."""

    model_config = ConfigDict(
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
