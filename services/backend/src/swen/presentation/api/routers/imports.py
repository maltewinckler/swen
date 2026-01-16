"""Imports router for transaction import history."""

import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from swen.application.queries.integration import ListImportsQuery
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()


class ImportResponse(BaseModel):
    """Response schema for a transaction import record."""

    id: UUID = Field(description="Import record unique identifier")
    bank_transaction_id: UUID = Field(description="Bank transaction UUID reference")
    status: str = Field(
        description="Import status: success, failed, pending, duplicate, skipped",
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    transaction_id: Optional[UUID] = Field(
        None,
        description="Created accounting transaction UUID (if successful)",
    )
    created_at: datetime = Field(description="When the import was attempted")
    imported_at: Optional[datetime] = Field(
        None,
        description="When successfully imported",
    )

    model_config = ConfigDict(
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


class ImportListResponse(BaseModel):
    """Response for listing import records."""

    imports: list[ImportResponse]
    count: int = Field(description="Number of imports in response")
    status_counts: dict[str, int] = Field(
        description="Count by status (success, failed, etc.)",
    )

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


class ImportStatisticsResponse(BaseModel):
    """Overall import statistics with date range info."""

    iban: Optional[str] = Field(None, description="IBAN filter (null for global)")
    total: int = Field(description="Total imports")
    success: int = Field(description="Successfully imported")
    failed: int = Field(description="Failed imports")
    pending: int = Field(description="Pending review")
    duplicate: int = Field(description="Duplicate (already imported)")
    skipped: int = Field(description="Skipped (filtered out)")
    last_import_at: Optional[datetime] = Field(
        None,
        description="Most recent successful import",
    )
    oldest_import_at: Optional[datetime] = Field(
        None,
        description="Oldest successful import",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "iban": None,
                "total": 150,
                "success": 140,
                "failed": 2,
                "pending": 3,
                "duplicate": 5,
                "skipped": 0,
                "last_import_at": "2024-12-15T10:30:00Z",
                "oldest_import_at": "2024-06-01T09:00:00Z",
            },
        },
    )


DaysFilter = Annotated[
    int,
    Query(ge=1, le=365, description="Days to look back"),
]
LimitFilter = Annotated[
    int,
    Query(ge=1, le=500, description="Maximum imports to return"),
]
FailedOnlyFilter = Annotated[
    bool,
    Query(description="Only show failed imports"),
]
IbanFilter = Annotated[
    str | None,
    Query(description="Filter by bank account IBAN"),
]


@router.get(
    "",
    summary="List import history",
    responses={
        200: {"description": "List of import records"},
    },
)
async def list_imports(
    factory: RepoFactory,
    days: DaysFilter = 30,
    limit: LimitFilter = 50,
    failed_only: FailedOnlyFilter = False,
    iban: IbanFilter = None,
) -> ImportListResponse:
    """
    List transaction import history.

    Shows the history of bank transaction imports, including:
    - Successfully imported transactions
    - Failed imports (with error messages)
    - Duplicate detections
    - Pending imports awaiting review

    **Use cases:**
    - Troubleshoot sync issues
    - Review failed imports
    - Audit import history
    """
    query = ListImportsQuery.from_factory(factory)
    result = await query.execute(
        days=days,
        limit=limit,
        failed_only=failed_only,
        iban_filter=iban,
    )

    imports = [
        ImportResponse(
            id=imp.id,
            bank_transaction_id=imp.bank_transaction_id,
            status=imp.status.value,
            error_message=imp.error_message,
            transaction_id=imp.accounting_transaction_id,
            created_at=imp.created_at,
            imported_at=imp.imported_at,
        )
        for imp in result.imports
    ]

    return ImportListResponse(
        imports=imports,
        count=result.total_count,
        status_counts=result.status_counts,
    )


@router.get(
    "/statistics",
    summary="Get import statistics",
    responses={
        200: {"description": "Import statistics"},
    },
)
async def get_import_statistics(
    factory: RepoFactory,
    iban: IbanFilter = None,
) -> ImportStatisticsResponse:
    """
    Get import statistics with date range info.

    Returns counts of imports by status, plus timestamps for the
    oldest and most recent successful imports.

    **Parameters:**
    - `iban`: Optional filter by bank account IBAN.
              If not provided, returns global statistics.

    **Use cases:**
    - Dashboard widgets showing import health
    - Per-account sync status display
    - Monitoring import activity
    """
    query = ListImportsQuery.from_factory(factory)
    stats = await query.get_statistics(iban=iban)

    return ImportStatisticsResponse(
        iban=stats.iban,
        total=stats.total_imports,
        success=stats.successful_imports,
        failed=stats.failed_imports,
        pending=stats.pending_imports,
        duplicate=stats.duplicate_imports,
        skipped=stats.skipped_imports,
        last_import_at=stats.last_import_at,
        oldest_import_at=stats.oldest_import_at,
    )
