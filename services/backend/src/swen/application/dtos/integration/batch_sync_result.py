"""DTO for batch transaction sync command result."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from swen.application.dtos.integration.sync_result import SyncResult


@dataclass(frozen=True)
class OpeningBalanceInfo:
    """Info about a created opening balance."""

    iban: str
    amount: Optional[Decimal]


@dataclass(frozen=True)
class AccountSyncStats:
    """Statistics for a single account sync."""

    iban: str
    fetched: int
    imported: int
    skipped: int
    failed: int


@dataclass
class BatchSyncResult:
    """Result of batch transaction sync across multiple accounts."""

    synced_at: datetime
    start_date: date
    end_date: date
    auto_post: bool

    # Aggregate counts
    total_fetched: int = 0
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0

    # Per-account breakdown
    account_stats: list[AccountSyncStats] = field(default_factory=list)

    # Opening balances created
    opening_balances: list[OpeningBalanceInfo] = field(default_factory=list)

    # Errors encountered
    errors: list[str] = field(default_factory=list)

    # Warning about missing opening balance account
    opening_balance_account_missing: bool = False

    @property
    def success(self) -> bool:
        return self.total_failed == 0 or self.total_imported > 0

    @property
    def accounts_synced(self) -> int:
        return len(self.account_stats)

    def add_result(self, result: SyncResult) -> None:
        self.total_fetched += result.transactions_fetched
        self.total_imported += result.transactions_imported
        self.total_skipped += result.transactions_skipped
        self.total_failed += result.transactions_failed

        self.account_stats.append(
            AccountSyncStats(
                iban=result.iban,
                fetched=result.transactions_fetched,
                imported=result.transactions_imported,
                skipped=result.transactions_skipped,
                failed=result.transactions_failed,
            ),
        )

        if result.error_message:
            self.errors.append(f"{result.iban}: {result.error_message}")

        if result.opening_balance_created:
            self.opening_balances.append(
                OpeningBalanceInfo(
                    iban=result.iban,
                    amount=result.opening_balance_amount,
                ),
            )

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "synced_at": self.synced_at.isoformat(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "auto_post": self.auto_post,
            "total_fetched": self.total_fetched,
            "total_imported": self.total_imported,
            "total_skipped": self.total_skipped,
            "total_failed": self.total_failed,
            "accounts_synced": self.accounts_synced,
            "account_stats": [
                {
                    "iban": s.iban,
                    "fetched": s.fetched,
                    "imported": s.imported,
                    "skipped": s.skipped,
                    "failed": s.failed,
                }
                for s in self.account_stats
            ],
            "opening_balances": [
                {
                    "iban": ob.iban,
                    "amount": float(ob.amount) if ob.amount else None,
                }
                for ob in self.opening_balances
            ],
            "errors": self.errors,
            "opening_balance_account_missing": self.opening_balance_account_missing,
        }
