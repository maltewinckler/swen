"""Immutable result DTO for batch transaction sync runs.

`BatchSyncResult` is a frozen value type with tuple-typed collections. It is
constructed exclusively via `BatchSyncResultBuilder`, which lives in the
local scope of the orchestrating command. Once `build()` returns, the result
is fully immutable and safe to publish through `SyncEventPublisher`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from swen.application.dtos.integration.sync_result import SyncResult


@dataclass(frozen=True)
class OpeningBalanceInfo:
    """Info about a created opening balance for an account."""

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


@dataclass(frozen=True)
class BatchSyncResult:
    """Immutable result of a batch transaction sync across multiple accounts.

    Constructed via `BatchSyncResultBuilder.build()` — never instantiated
    directly by the orchestration loop.
    """

    synced_at: datetime
    start_date: date
    end_date: date
    auto_post: bool

    total_fetched: int = 0
    total_imported: int = 0
    total_skipped: int = 0
    total_failed: int = 0

    # Per-account breakdown (immutable).
    account_stats: tuple[AccountSyncStats, ...] = ()

    # Opening balances created during this run (immutable).
    opening_balances: tuple[OpeningBalanceInfo, ...] = ()

    # Error strings (one per failure), pre-formatted as `"<iban>: <error>"`.
    errors: tuple[str, ...] = ()

    # Warning about a missing opening-balance equity account.
    opening_balance_account_missing: bool = False

    @property
    def success(self) -> bool:
        return self.total_failed == 0 or self.total_imported > 0

    @property
    def accounts_synced(self) -> int:
        return len(self.account_stats)

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
                    "amount": float(ob.amount) if ob.amount is not None else None,
                }
                for ob in self.opening_balances
            ],
            "errors": list(self.errors),
            "opening_balance_account_missing": self.opening_balance_account_missing,
        }


class BatchSyncResultBuilder:
    """Local-only mutable builder for `BatchSyncResult`.

    The builder is the only way to construct a `BatchSyncResult`. It is
    expected to live within the local scope of `SyncBankAccountsCommand.execute`
    and never leak to callers. Once `build()` is invoked, the resulting
    `BatchSyncResult` is fully immutable.
    """

    def __init__(
        self,
        synced_at: datetime,
        start_date: date,
        end_date: date,
        auto_post: bool,
        opening_balance_account_missing: bool,
    ):
        self._synced_at = synced_at
        self._start_date = start_date
        self._end_date = end_date
        self._auto_post = auto_post
        self._opening_balance_account_missing = opening_balance_account_missing

        self._total_fetched = 0
        self._total_imported = 0
        self._total_skipped = 0
        self._total_failed = 0

        self._account_stats: list[AccountSyncStats] = []
        self._opening_balances: list[OpeningBalanceInfo] = []
        self._errors: list[str] = []

    def add_account(self, sync_result: SyncResult) -> None:
        """Aggregate a per-account `SyncResult` into the builder.

        Updates the running totals, appends per-account stats, captures any
        opening balance that was created, and records the result's
        `error_message` (if present) as an error entry. The conservation
        invariant on totals vs. account_stats is preserved.
        """
        self._total_fetched += sync_result.transactions_fetched
        self._total_imported += sync_result.transactions_imported
        self._total_skipped += sync_result.transactions_skipped
        self._total_failed += sync_result.transactions_failed

        self._account_stats.append(
            AccountSyncStats(
                iban=sync_result.iban,
                fetched=sync_result.transactions_fetched,
                imported=sync_result.transactions_imported,
                skipped=sync_result.transactions_skipped,
                failed=sync_result.transactions_failed,
            ),
        )

        if sync_result.error_message:
            self._errors.append(f"{sync_result.iban}: {sync_result.error_message}")

        if sync_result.opening_balance_created:
            self._opening_balances.append(
                OpeningBalanceInfo(
                    iban=sync_result.iban,
                    amount=sync_result.opening_balance_amount,
                ),
            )

    def add_error(self, iban: str, error: str) -> None:
        """Record a per-account error that was not captured in a `SyncResult`.

        Used when `sync_account` itself raises and no `SyncResult` is
        produced. The stored format matches the legacy convention
        `"<iban>: <error>"` so consumers do not need to special-case the
        source.
        """
        self._errors.append(f"{iban}: {error}")

    def widen_period(self, start_date: date, end_date: date) -> None:
        """Expand the run's date window to cover the observed range.

        Used by `SyncBankAccountsCommand.execute` when a per-account result
        from an adaptive period reports a wider observed window than the
        builder's current bounds.
        """
        self._start_date = min(self._start_date, start_date)
        self._end_date = max(self._end_date, end_date)

    def build(self) -> BatchSyncResult:
        """Return the immutable `BatchSyncResult` and freeze its contents."""
        return BatchSyncResult(
            synced_at=self._synced_at,
            start_date=self._start_date,
            end_date=self._end_date,
            auto_post=self._auto_post,
            total_fetched=self._total_fetched,
            total_imported=self._total_imported,
            total_skipped=self._total_skipped,
            total_failed=self._total_failed,
            account_stats=tuple(self._account_stats),
            opening_balances=tuple(self._opening_balances),
            errors=tuple(self._errors),
            opening_balance_account_missing=self._opening_balance_account_missing,
        )
