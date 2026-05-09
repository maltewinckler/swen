"""Sync schemas for API request/response models."""

from datetime import date
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

    days: Optional[int] = Field(
        default=None,
        ge=1,
        le=730,
        description=(
            "Number of days to fetch transactions for (max 2 years). "
            "If null/omitted, uses adaptive mode: first sync uses 90 days, "
            "subsequent syncs use last sync date to today."
        ),
    )
    blz: Optional[str] = Field(
        None,
        description="Sync only accounts from this bank (by BLZ/bank code)",
    )

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


class AccountSyncRecommendationResponse(BaseModel):
    """Sync recommendation for a single bank account.

    Helps the frontend determine whether this is a first-time sync
    and what date range to use.
    """

    iban: str = Field(..., description="Bank account IBAN")
    is_first_sync: bool = Field(
        ...,
        description="True if this account has never been synced successfully",
    )
    recommended_start_date: Optional[date] = Field(
        None,
        description=(
            "Recommended start date for sync. "
            "None for first sync (user should specify days)."
        ),
    )
    last_successful_sync_date: Optional[date] = Field(
        None,
        description="Date of the most recent successfully imported transaction",
    )
    successful_import_count: int = Field(
        ...,
        description="Number of transactions successfully imported for this account",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "First sync (no history)",
                    "value": {
                        "iban": "DE89370400440532013000",
                        "is_first_sync": True,
                        "recommended_start_date": None,
                        "last_successful_sync_date": None,
                        "successful_import_count": 0,
                    },
                },
                {
                    "summary": "Subsequent sync (has history)",
                    "value": {
                        "iban": "DE89370400440532013000",
                        "is_first_sync": False,
                        "recommended_start_date": "2024-12-01",
                        "last_successful_sync_date": "2024-12-03",
                        "successful_import_count": 150,
                    },
                },
            ],
        },
    )


class SyncRecommendationResponse(BaseModel):
    """Response schema for sync recommendation query.

    Provides per-account sync recommendations to help the frontend
    implement adaptive synchronization:

    1. If `has_first_sync_accounts` is true: Show a dialog asking the user
       how many days of history to load for the new accounts.
     2. Otherwise: Use adaptive sync via `POST /sync/run/stream` with no days parameter.
    """

    accounts: list[AccountSyncRecommendationResponse] = Field(
        ...,
        description="Per-account sync recommendations",
    )
    has_first_sync_accounts: bool = Field(
        ...,
        description=(
            "True if any account needs first-time sync. "
            "Frontend should prompt user for number of days to load."
        ),
    )
    total_accounts: int = Field(
        ...,
        description="Total number of mapped bank accounts",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accounts": [
                    {
                        "iban": "DE89370400440532013000",
                        "is_first_sync": False,
                        "recommended_start_date": "2024-12-01",
                        "last_successful_sync_date": "2024-12-03",
                        "successful_import_count": 150,
                    },
                    {
                        "iban": "DE91100000000123456789",
                        "is_first_sync": True,
                        "recommended_start_date": None,
                        "last_successful_sync_date": None,
                        "successful_import_count": 0,
                    },
                ],
                "has_first_sync_accounts": True,
                "total_accounts": 2,
            },
        },
    )
