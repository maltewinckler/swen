"""Dashboard summary query - aggregates financial data for display.

This query encapsulates the business logic for calculating dashboard metrics,
keeping the CLI layer focused on presentation only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.settings.repositories import UserSettingsRepository
from swen.domain.shared.time import ensure_tz_aware, utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


def _date_in_range(dt: datetime, start: datetime, end: datetime) -> bool:
    """Check if datetime is in range, handling timezone-naive/aware mismatches."""
    return ensure_tz_aware(start) <= ensure_tz_aware(dt) < ensure_tz_aware(end)


@dataclass
class DashboardSummary:
    """Dashboard summary data."""

    period_label: str
    account_balances: dict[Account, Decimal]
    total_income: Decimal
    total_expenses: Decimal
    category_spending: dict[str, Decimal]
    recent_transactions: list[Transaction]
    all_accounts: list[Account]
    draft_count: int
    posted_count: int


class DashboardSummaryQuery:
    """Query to generate dashboard summary data."""

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        settings_repository: Optional[UserSettingsRepository] = None,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._settings_repo = settings_repository
        self._balance_service = AccountBalanceService()

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DashboardSummaryQuery:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            settings_repository=factory.user_settings_repository(),
        )

    async def _get_show_drafts_preference(self) -> bool:
        if not self._settings_repo:
            msg = "Cannot load user settings: settings_repository not provided."
            raise ValueError(msg)

        settings = await self._settings_repo.get_or_create()
        return settings.display.show_draft_transactions

    def _calculate_period(
        self,
        days: Optional[int],
        month: Optional[str],
    ) -> tuple[datetime, datetime, str]:
        now = utc_now()

        if days is not None and days > 0:
            return (now - timedelta(days=days), now, f"Last {days} days")

        if month:
            try:
                year, mon = map(int, month.split("-"))
                start_date = datetime(year, mon, 1, tzinfo=timezone.utc)
                end_date = self._next_month_start(year, mon)
                return (start_date, end_date, start_date.strftime("%B %Y"))
            except (ValueError, AttributeError) as e:
                msg = "Invalid month format. Use YYYY-MM"
                raise ValueError(msg) from e

        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        end_date = self._next_month_start(now.year, now.month)
        return (start_date, end_date, start_date.strftime("%B %Y"))

    def _next_month_start(self, year: int, month: int) -> datetime:
        if month == 12:
            return datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        return datetime(year, month + 1, 1, tzinfo=timezone.utc)

    def _calculate_account_balances(
        self,
        accounts: list[Account],
        transactions: list[Transaction],
    ) -> dict[Account, Decimal]:
        balances: dict[Account, Decimal] = {}
        for account in accounts:
            if account.account_type == AccountType.ASSET:
                account_txns = [t for t in transactions if t.involves_account(account)]
                balance = self._balance_service.calculate_balance(
                    account=account,
                    transactions=account_txns,
                    include_drafts=True,
                )
                balances[account] = balance.amount
        return balances

    def _calculate_income_expenses(
        self,
        transactions: list[Transaction],
    ) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
        total_income = Decimal("0")
        total_expenses = Decimal("0")
        category_spending: dict[str, Decimal] = defaultdict(Decimal)

        for txn in transactions:
            for entry in txn.entries:
                if entry.account.account_type == AccountType.INCOME:
                    if not entry.is_debit():
                        total_income += entry.credit.amount
                elif (
                    entry.account.account_type == AccountType.EXPENSE
                    and entry.is_debit()
                ):
                    total_expenses += entry.debit.amount
                    category_spending[entry.account.name] += entry.debit.amount

        return (total_income, total_expenses, dict(category_spending))

    async def execute(
        self,
        days: Optional[int] = None,
        month: Optional[str] = None,
        show_drafts: Optional[bool] = None,
    ) -> DashboardSummary:
        if show_drafts is None:
            show_drafts = await self._get_show_drafts_preference()

        all_accounts = await self._account_repo.find_all_active()
        if show_drafts:
            all_transactions = await self._transaction_repo.find_all()
        else:
            all_transactions = await self._transaction_repo.find_posted_transactions()

        start_date, end_date, period_label = self._calculate_period(days, month)

        period_transactions = [
            t for t in all_transactions if _date_in_range(t.date, start_date, end_date)
        ]

        draft_count = sum(1 for t in all_transactions if not t.is_posted)
        posted_count = sum(1 for t in all_transactions if t.is_posted)

        account_balances = self._calculate_account_balances(
            all_accounts,
            all_transactions,
        )
        (
            total_income,
            total_expenses,
            category_spending,
        ) = self._calculate_income_expenses(period_transactions)

        recent_transactions = sorted(
            all_transactions,
            key=lambda t: t.date,
            reverse=True,
        )[:10]

        return DashboardSummary(
            period_label=period_label,
            account_balances=account_balances,
            total_income=total_income,
            total_expenses=total_expenses,
            category_spending=category_spending,
            recent_transactions=recent_transactions,
            all_accounts=all_accounts,
            draft_count=draft_count,
            posted_count=posted_count,
        )
