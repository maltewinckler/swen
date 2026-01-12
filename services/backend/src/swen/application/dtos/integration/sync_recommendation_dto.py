"""DTO for sync recommendation query result."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class AccountSyncRecommendationDTO:
    """Sync recommendation for a single account.

    Provides information needed for adaptive synchronization:
    - Whether this is a first-time sync (no history)
    - Recommended start date based on sync history
    - Statistics about previous syncs
    """

    iban: str
    is_first_sync: bool
    recommended_start_date: Optional[date]
    last_successful_sync_date: Optional[date]
    successful_import_count: int

    def to_dict(self) -> dict:
        return {
            "iban": self.iban,
            "is_first_sync": self.is_first_sync,
            "recommended_start_date": (
                self.recommended_start_date.isoformat()
                if self.recommended_start_date
                else None
            ),
            "last_successful_sync_date": (
                self.last_successful_sync_date.isoformat()
                if self.last_successful_sync_date
                else None
            ),
            "successful_import_count": self.successful_import_count,
        }


@dataclass(frozen=True)
class SyncRecommendationResultDTO:
    """Result of sync recommendation query.

    Provides per-account sync recommendations to help implement
    adaptive synchronization in the frontend.
    """

    accounts: tuple[AccountSyncRecommendationDTO, ...]
    has_first_sync_accounts: bool
    total_accounts: int

    def to_dict(self) -> dict:
        return {
            "accounts": [acc.to_dict() for acc in self.accounts],
            "has_first_sync_accounts": self.has_first_sync_accounts,
            "total_accounts": self.total_accounts,
        }

    @property
    def first_sync_accounts(self) -> tuple[AccountSyncRecommendationDTO, ...]:
        return tuple(acc for acc in self.accounts if acc.is_first_sync)

    @property
    def subsequent_sync_accounts(self) -> tuple[AccountSyncRecommendationDTO, ...]:
        return tuple(acc for acc in self.accounts if not acc.is_first_sync)
