"""Sync schemas for API request/response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SyncRunRequest(BaseModel):
    """Request schema for running a bank transaction sync.

    All fields are optional - sensible defaults will be used.

    Adaptive Sync Mode:
    When `days` is null/not provided, adaptive sync is used where each account's
    date range is determined based on its import history:
    - First sync (no history): Uses 90 days
    - Subsequent syncs: From last successful sync date + 1 day to today
    """

    days: Optional[int] = Field(None, ge=1, le=730)
    blz: Optional[str] = Field(None)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Adaptive sync (recommended for regular use)",
                    "value": {},
                },
                {
                    "summary": "First sync with specific days",
                    "value": {"days": 90},
                },
                {
                    "summary": "Quick sync (last 7 days)",
                    "value": {"days": 7},
                },
            ],
        },
    )


class SyncStatusResponse(BaseModel):
    """Response schema for overall sync status and statistics.

    Shows aggregate counts across all historical sync operations.
    """

    success_count: int = Field(..., description="Successfully imported transactions")
    failed_count: int = Field(..., description="Transactions that failed to import")
    pending_count: int = Field(..., description="Transactions awaiting processing")
    duplicate_count: int = Field(..., description="Transactions detected as duplicates")
    skipped_count: int = Field(..., description="Transactions intentionally skipped")
    total_count: int = Field(..., description="Total import records in system")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success_count": 1250,
                "failed_count": 3,
                "pending_count": 0,
                "duplicate_count": 87,
                "skipped_count": 12,
                "total_count": 1352,
            },
        },
    )
