"""Sync schemas for API request/response models."""

from datetime import date, datetime
from decimal import Decimal
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
    iban: Optional[str] = Field(
        None,
        description="Sync only this specific account by IBAN (default: sync all accounts)",
    )
    blz: Optional[str] = Field(
        None,
        description="Sync only accounts from this bank (by BLZ/bank code)",
    )
    auto_post: Optional[bool] = Field(
        None,
        description="Auto-post transactions after import (None = use user preference, typically False)",
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
                {
                    "summary": "Sync specific account with auto-post",
                    "value": {
                        "days": 30,
                        "iban": "DE89370400440532013000",
                        "auto_post": True,
                    },
                },
            ],
        },
    )


class AccountSyncStatsResponse(BaseModel):
    """Statistics for a single account's sync operation."""

    iban: str = Field(..., description="Bank account IBAN that was synced")
    fetched: int = Field(..., description="Total transactions received from bank")
    imported: int = Field(..., description="New transactions successfully imported")
    skipped: int = Field(
        ..., description="Transactions skipped (already exist in system)"
    )
    failed: int = Field(
        ..., description="Transactions that failed to import (see errors)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "iban": "DE89370400440532013000",
                "fetched": 25,
                "imported": 20,
                "skipped": 5,
                "failed": 0,
            },
        },
    )


class OpeningBalanceResponse(BaseModel):
    """Info about an opening balance created during sync.

    Opening balances are auto-created when syncing a new account
    to set the initial balance correctly.
    """

    iban: str = Field(..., description="Bank account IBAN")
    amount: Optional[Decimal] = Field(
        None, description="Opening balance amount (from bank statement)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "iban": "DE89370400440532013000",
                "amount": "1250.00",
            },
        },
    )


class SyncRunResponse(BaseModel):
    """Response schema for sync run result.

    Contains detailed statistics about the sync operation,
    including per-account breakdowns and any errors encountered.
    """

    success: bool = Field(
        ..., description="Whether sync completed without critical errors"
    )
    synced_at: datetime = Field(..., description="When the sync was performed")
    start_date: date = Field(..., description="Start of the date range that was synced")
    end_date: date = Field(..., description="End of the date range (typically today)")
    auto_post: bool = Field(
        ..., description="Whether imported transactions were automatically posted"
    )

    # Aggregate counts
    total_fetched: int = Field(
        ..., description="Total transactions received from all banks"
    )
    total_imported: int = Field(
        ..., description="New transactions successfully imported"
    )
    total_skipped: int = Field(..., description="Transactions skipped (duplicates)")
    total_failed: int = Field(..., description="Transactions that failed to import")
    accounts_synced: int = Field(
        ..., description="Number of bank accounts that were synced"
    )

    # Per-account breakdown
    account_stats: list[AccountSyncStatsResponse] = Field(
        ...,
        description="Detailed statistics per bank account",
    )

    # Opening balances created
    opening_balances: list[OpeningBalanceResponse] = Field(
        ...,
        description="Opening balances created for new accounts",
    )

    # Warnings and errors
    errors: list[str] = Field(..., description="Error messages (if any)")
    opening_balance_account_missing: bool = Field(
        ...,
        description="Warning: could not create opening balance (missing equity account)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "synced_at": "2024-12-05T15:30:00Z",
                "start_date": "2024-09-07",
                "end_date": "2024-12-05",
                "auto_post": False,
                "total_fetched": 45,
                "total_imported": 38,
                "total_skipped": 7,
                "total_failed": 0,
                "accounts_synced": 2,
                "account_stats": [
                    {
                        "iban": "DE89370400440532013000",
                        "fetched": 25,
                        "imported": 20,
                        "skipped": 5,
                        "failed": 0,
                    },
                    {
                        "iban": "DE91100000000123456789",
                        "fetched": 20,
                        "imported": 18,
                        "skipped": 2,
                        "failed": 0,
                    },
                ],
                "opening_balances": [],
                "errors": [],
                "opening_balance_account_missing": False,
            },
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
    2. Otherwise: Use adaptive sync (POST /sync/run with no days parameter).
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
