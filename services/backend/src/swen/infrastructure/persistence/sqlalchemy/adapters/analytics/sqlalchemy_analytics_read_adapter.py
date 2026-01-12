"""SQLAlchemy implementation of AnalyticsReadPort.

We intentionally avoid DB-specific "group by month" functions here (strftime/to_char)
and instead fetch only the necessary entry rows and aggregate in Python. This:
- avoids loading full Transaction aggregates (better than find_all())
- keeps the port stable for future DB backends
- keeps this adapter implementation portable across SQLite/Postgres today

If/when scale grows, we can replace the Python aggregation with true SQL GROUP BY
per backend, or switch to rollup tables without changing the port.
"""

from __future__ import annotations

from calendar import month_name
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.application.dtos.analytics import (
    BreakdownItem,
    CategoryComparison,
    CategoryTimeSeriesDataPoint,
    CategoryTimeSeriesResult,
    IncomeBreakdownResult,
    MonthComparisonResult,
    SpendingBreakdownResult,
    TimeSeriesDataPoint,
    TimeSeriesResult,
    TopExpenseItem,
    TopExpensesResult,
)
from swen.application.ports.analytics import AnalyticsReadPort
from swen.domain.accounting.entities import AccountType
from swen.domain.shared.time import ensure_tz_aware, utc_now
from swen.infrastructure.persistence.sqlalchemy.models.accounting.account_model import (
    AccountModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.accounting.journal_entry_model import (  # NOQA: E501
    JournalEntryModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.accounting.transaction_model import (  # NOQA: E501
    TransactionModel,
)

if TYPE_CHECKING:
    from swen.application.context import UserContext


def _get_month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _get_month_label(year: int, month: int) -> str:
    return f"{month_name[month]} {year}"


def _first_day_of_month(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, tzinfo=dt.tzinfo)


def _next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1, tzinfo=dt.tzinfo)
    return datetime(dt.year, dt.month + 1, 1, tzinfo=dt.tzinfo)


class SqlAlchemyAnalyticsReadAdapter(AnalyticsReadPort):
    """SQLAlchemy analytics read adapter."""

    def __init__(self, session: AsyncSession, user_context: UserContext):
        self._session = session
        self._user_id = user_context.user_id

    async def spending_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> CategoryTimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        stmt = (
            select(
                TransactionModel.date,
                AccountModel.name,
                AccountModel.id,
                JournalEntryModel.debit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.EXPENSE.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                JournalEntryModel.debit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        monthly_spending: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal),
        )
        totals_by_category: dict[str, Decimal] = defaultdict(Decimal)
        all_categories: set[str] = set()

        for txn_date_, category_name, _, debit_amount in rows:
            txn_date = ensure_tz_aware(txn_date_)
            month_key = _get_month_key(txn_date.year, txn_date.month)
            monthly_spending[month_key][category_name] += Decimal(debit_amount)
            totals_by_category[category_name] += Decimal(debit_amount)
            all_categories.add(category_name)

        # Build data points for each month in range
        data_points: list[CategoryTimeSeriesDataPoint] = []
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            categories = dict(monthly_spending.get(month_key, {}))
            total = sum(categories.values(), Decimal("0"))
            data_points.append(
                CategoryTimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    categories=categories,
                    total=total,
                ),
            )
            current = _next_month(current)

        sorted_categories = sorted(
            all_categories,
            key=lambda c: totals_by_category.get(c, Decimal("0")),
            reverse=True,
        )

        return CategoryTimeSeriesResult(
            data_points=data_points,
            categories=sorted_categories,
            currency="EUR",
            totals_by_category=dict(totals_by_category),
        )

    async def single_account_spending_over_time(
        self,
        *,
        account_id: UUID,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        # Query for specific account only
        stmt = (
            select(
                TransactionModel.date,
                JournalEntryModel.debit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.id == account_id,
                AccountModel.account_type == AccountType.EXPENSE.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                JournalEntryModel.debit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        # Aggregate by month
        monthly_spending: dict[str, Decimal] = defaultdict(Decimal)
        for txn_date_, debit_amount in rows:
            txn_date = ensure_tz_aware(txn_date_)
            month_key = _get_month_key(txn_date.year, txn_date.month)
            monthly_spending[month_key] += Decimal(debit_amount)

        # Build data points for each month in range
        data_points: list[TimeSeriesDataPoint] = []
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            value = monthly_spending.get(month_key, Decimal("0"))
            data_points.append(
                TimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    value=value,
                ),
            )
            current = _next_month(current)

        return self._build_time_series_result(data_points, use_sum_as_total=True)

    async def spending_breakdown(
        self,
        *,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> SpendingBreakdownResult:
        start_date, end_date, period_label = self._calculate_breakdown_period(
            month,
            days,
        )

        stmt = (
            select(
                AccountModel.name,
                AccountModel.id,
                JournalEntryModel.debit_amount,
            )
            .join(JournalEntryModel, JournalEntryModel.account_id == AccountModel.id)
            .join(
                TransactionModel,
                TransactionModel.id == JournalEntryModel.transaction_id,
            )
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.EXPENSE.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_date,
                JournalEntryModel.debit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        spending_by_category: dict[str, Decimal] = defaultdict(Decimal)
        account_ids: dict[str, str] = {}
        for category_name, account_id, debit_amount in rows:
            spending_by_category[category_name] += Decimal(debit_amount)
            account_ids[category_name] = str(account_id)

        total = sum(spending_by_category.values(), Decimal("0"))

        items: list[BreakdownItem] = []
        for category, amount in sorted(
            spending_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            percentage = (amount / total * 100) if total > 0 else Decimal("0")
            items.append(
                BreakdownItem(
                    category=category,
                    amount=amount,
                    percentage=percentage.quantize(Decimal("0.1")),
                    account_id=account_ids.get(category, ""),
                ),
            )

        return SpendingBreakdownResult(
            period_label=period_label,
            items=items,
            total=total,
            currency="EUR",
            category_count=len(items),
        )

    async def income_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        stmt = (
            select(
                TransactionModel.date,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.INCOME.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                JournalEntryModel.credit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        monthly_income: dict[str, Decimal] = defaultdict(Decimal)
        for txn_date_, credit_amount in rows:
            txn_date = ensure_tz_aware(txn_date_)
            month_key = _get_month_key(txn_date.year, txn_date.month)
            monthly_income[month_key] += Decimal(credit_amount)

        data_points: list[TimeSeriesDataPoint] = []
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            value = monthly_income.get(month_key, Decimal("0"))
            data_points.append(
                TimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    value=value,
                ),
            )
            current = _next_month(current)

        return self._build_time_series_result(data_points, use_sum_as_total=True)

    async def income_breakdown(
        self,
        *,
        month: str | None = None,
        days: int | None = None,
        include_drafts: bool = False,
    ) -> IncomeBreakdownResult:
        start_date, end_date, period_label = self._calculate_breakdown_period(
            month,
            days,
        )

        stmt = (
            select(
                AccountModel.name,
                AccountModel.id,
                JournalEntryModel.credit_amount,
            )
            .join(JournalEntryModel, JournalEntryModel.account_id == AccountModel.id)
            .join(
                TransactionModel,
                TransactionModel.id == JournalEntryModel.transaction_id,
            )
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.INCOME.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_date,
                JournalEntryModel.credit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        income_by_source: dict[str, Decimal] = defaultdict(Decimal)
        account_ids: dict[str, str] = {}
        for source_name, account_id, credit_amount in rows:
            income_by_source[source_name] += Decimal(credit_amount)
            account_ids[source_name] = str(account_id)

        total = sum(income_by_source.values(), Decimal("0"))

        items: list[BreakdownItem] = []
        for source, amount in sorted(
            income_by_source.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            percentage = (amount / total * 100) if total > 0 else Decimal("0")
            items.append(
                BreakdownItem(
                    category=source,
                    amount=amount,
                    percentage=percentage.quantize(Decimal("0.1")),
                    account_id=account_ids.get(source, ""),
                ),
            )

        return IncomeBreakdownResult(
            period_label=period_label,
            items=items,
            total=total,
            currency="EUR",
        )

    async def net_income_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        stmt = (
            select(
                TransactionModel.date,
                AccountModel.account_type,
                JournalEntryModel.debit_amount,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                AccountModel.account_type.in_(
                    [AccountType.INCOME.value, AccountType.EXPENSE.value],
                ),
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        monthly_income: dict[str, Decimal] = defaultdict(Decimal)
        monthly_expenses: dict[str, Decimal] = defaultdict(Decimal)
        for txn_date_, account_type, debit_amount, credit_amount in rows:
            txn_date = ensure_tz_aware(txn_date_)
            month_key = _get_month_key(txn_date.year, txn_date.month)

            if account_type == AccountType.INCOME.value and Decimal(credit_amount) > 0:
                monthly_income[month_key] += Decimal(credit_amount)
            elif (
                account_type == AccountType.EXPENSE.value and Decimal(debit_amount) > 0
            ):
                monthly_expenses[month_key] += Decimal(debit_amount)

        data_points: list[TimeSeriesDataPoint] = []
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            income = monthly_income.get(month_key, Decimal("0"))
            expenses = monthly_expenses.get(month_key, Decimal("0"))
            net = income - expenses
            data_points.append(
                TimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    value=net,
                ),
            )
            current = _next_month(current)

        return self._build_time_series_result(data_points, use_sum_as_total=True)

    async def savings_rate_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        stmt = (
            select(
                TransactionModel.date,
                AccountModel.account_type,
                JournalEntryModel.debit_amount,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                AccountModel.account_type.in_(
                    [AccountType.INCOME.value, AccountType.EXPENSE.value],
                ),
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        monthly_income: dict[str, Decimal] = defaultdict(Decimal)
        monthly_expenses: dict[str, Decimal] = defaultdict(Decimal)
        for txn_date_, account_type, debit_amount, credit_amount in rows:
            txn_date = ensure_tz_aware(txn_date_)
            month_key = _get_month_key(txn_date.year, txn_date.month)

            if account_type == AccountType.INCOME.value and Decimal(credit_amount) > 0:
                monthly_income[month_key] += Decimal(credit_amount)
            elif (
                account_type == AccountType.EXPENSE.value and Decimal(debit_amount) > 0
            ):
                monthly_expenses[month_key] += Decimal(debit_amount)

        data_points: list[TimeSeriesDataPoint] = []
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            income = monthly_income.get(month_key, Decimal("0"))
            expenses = monthly_expenses.get(month_key, Decimal("0"))

            if income > 0:
                savings = income - expenses
                rate = (savings / income * 100).quantize(Decimal("0.1"))
            else:
                rate = Decimal("0") if expenses == 0 else Decimal("-100")

            data_points.append(
                TimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    value=rate,
                ),
            )
            current = _next_month(current)

        values = [dp.value for dp in data_points]
        non_zero_values = [v for v in values if v != Decimal("0")]
        total = sum(values, Decimal("0"))
        average = (
            sum(non_zero_values, Decimal("0")) / len(non_zero_values)
            if non_zero_values
            else Decimal("0")
        )
        min_value = min(values) if values else Decimal("0")
        max_value = max(values) if values else Decimal("0")

        return TimeSeriesResult(
            data_points=data_points,
            currency="%",
            total=total,
            average=average.quantize(Decimal("0.1")),
            min_value=min_value,
            max_value=max_value,
        )

    async def net_worth_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = True,
    ) -> TimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        asset_ids, liability_ids = await self._load_balance_sheet_accounts()
        entry_rows = await self._query_balance_sheet_entries(
            end_exclusive,
            include_drafts,
        )

        data_points = self._calculate_net_worth_series(
            entry_rows,
            asset_ids,
            liability_ids,
            start_date,
            end_date,
        )

        return self._build_time_series_result(data_points)

    def _calculate_date_range(
        self,
        months: int,
        end_month: str | None,
    ) -> tuple[datetime, datetime]:
        if end_month:
            end_year, end_m = map(int, end_month.split("-"))
            end_date = datetime(end_year, end_m, 1, tzinfo=timezone.utc)
        else:
            now = utc_now()
            end_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        start_year = end_date.year
        start_month = end_date.month - months + 1
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = datetime(start_year, start_month, 1, tzinfo=timezone.utc)

        return start_date, end_date

    def _calculate_breakdown_period(
        self,
        month: str | None,
        days: int | None,
    ) -> tuple[datetime, datetime, str]:
        """Calculate date range and label for breakdown queries."""
        now = utc_now()

        if days:
            return (
                now - timedelta(days=days),
                now,
                f"Last {days} days",
            )

        if month:
            year, m = map(int, month.split("-"))
            start_date = datetime(year, m, 1, tzinfo=timezone.utc)
            return (
                start_date,
                _next_month(start_date),
                f"{month_name[m]} {year}",
            )

        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        return (
            start_date,
            _next_month(start_date),
            f"{month_name[now.month]} {now.year}",
        )

    async def _load_balance_sheet_accounts(self) -> tuple[list[str], list[str]]:
        account_rows = (
            await self._session.execute(
                select(
                    AccountModel.id,
                    AccountModel.account_type,
                ).where(
                    AccountModel.user_id == self._user_id,
                    AccountModel.account_type.in_(
                        [AccountType.ASSET.value, AccountType.LIABILITY.value],
                    ),
                ),
            )
        ).all()

        asset_ids: list[str] = []
        liability_ids: list[str] = []
        for acc_id, acc_type in account_rows:
            if acc_type == AccountType.ASSET.value:
                asset_ids.append(str(acc_id))
            elif acc_type == AccountType.LIABILITY.value:
                liability_ids.append(str(acc_id))

        return asset_ids, liability_ids

    async def _query_balance_sheet_entries(
        self,
        end_exclusive: datetime,
        include_drafts: bool,
    ) -> list[tuple]:
        stmt = (
            select(
                TransactionModel.date,
                AccountModel.id,
                AccountModel.account_type,
                JournalEntryModel.debit_amount,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type.in_(
                    [AccountType.ASSET.value, AccountType.LIABILITY.value],
                ),
                TransactionModel.date < end_exclusive,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        entry_rows = (await self._session.execute(stmt)).all()

        # Normalize and sort by date
        normalized = [
            (ensure_tz_aware(txn_date), acc_id, acc_type, debit_amount, credit_amount)
            for txn_date, acc_id, acc_type, debit_amount, credit_amount in entry_rows
        ]
        return sorted(normalized, key=lambda r: r[0])

    def _calculate_net_worth_series(
        self,
        entry_rows: list[tuple],
        asset_ids: list[str],
        liability_ids: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> list[TimeSeriesDataPoint]:
        balances_by_id: dict[str, Decimal] = defaultdict(Decimal)
        data_points: list[TimeSeriesDataPoint] = []
        idx = 0
        current = start_date

        while current <= end_date:
            as_of = _next_month(current)

            # Accumulate entries up to this month
            while idx < len(entry_rows) and entry_rows[idx][0] < as_of:
                _, acc_id, acc_type, debit_amount, credit_amount = entry_rows[idx]
                balances_by_id[str(acc_id)] += self._apply_balance_delta(
                    acc_type,
                    Decimal(debit_amount),
                    Decimal(credit_amount),
                )
                idx += 1

            net_worth = self._compute_net_worth(
                balances_by_id,
                asset_ids,
                liability_ids,
            )
            data_points.append(
                TimeSeriesDataPoint(
                    period=_get_month_key(current.year, current.month),
                    period_label=_get_month_label(current.year, current.month),
                    value=net_worth,
                ),
            )
            current = _next_month(current)

        return data_points

    def _apply_balance_delta(
        self,
        acc_type: str,
        debit: Decimal,
        credit: Decimal,
    ) -> Decimal:
        if acc_type == AccountType.ASSET.value:
            return debit - credit
        return credit - debit  # credit-normal

    def _compute_net_worth(
        self,
        balances_by_id: dict[str, Decimal],
        asset_ids: list[str],
        liability_ids: list[str],
    ) -> Decimal:
        total_assets = sum((balances_by_id[i] for i in asset_ids), Decimal("0"))
        total_liabilities = sum(
            (balances_by_id[i] for i in liability_ids),
            Decimal("0"),
        )
        return total_assets - total_liabilities

    def _build_time_series_result(
        self,
        data_points: list[TimeSeriesDataPoint],
        *,
        use_sum_as_total: bool = False,
        currency: str = "EUR",
    ) -> TimeSeriesResult:
        values = [dp.value for dp in data_points]
        total_sum = sum(values, Decimal("0"))
        latest = values[-1] if values else Decimal("0")
        average = total_sum / len(values) if values else Decimal("0")
        min_value = min(values) if values else Decimal("0")
        max_value = max(values) if values else Decimal("0")

        return TimeSeriesResult(
            data_points=data_points,
            currency=currency,
            total=total_sum if use_sum_as_total else latest,
            average=average,
            min_value=min_value,
            max_value=max_value,
        )

    async def balance_history_over_time(
        self,
        *,
        months: int = 12,
        end_month: str | None = None,
        include_drafts: bool = True,
    ) -> CategoryTimeSeriesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        # Load asset account list (user-scoped)
        account_rows = (
            await self._session.execute(
                select(AccountModel.id, AccountModel.name).where(
                    AccountModel.user_id == self._user_id,
                    AccountModel.account_type == AccountType.ASSET.value,
                ),
            )
        ).all()

        asset_ids = [str(acc_id) for acc_id, _name in account_rows]
        asset_name_by_id = {str(acc_id): name for acc_id, name in account_rows}

        # Fetch all relevant asset entries up to end_exclusive (no lower bound)
        stmt = (
            select(
                TransactionModel.date,
                AccountModel.id,
                JournalEntryModel.debit_amount,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.ASSET.value,
                TransactionModel.date < end_exclusive,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        entry_rows = (await self._session.execute(stmt)).all()

        normalized_rows = [
            (ensure_tz_aware(txn_date), acc_id, debit_amount, credit_amount)
            for txn_date, acc_id, debit_amount, credit_amount in entry_rows
        ]

        entry_rows = sorted(normalized_rows, key=lambda r: r[0])
        balances_by_id: dict[str, Decimal] = defaultdict(Decimal)

        data_points: list[CategoryTimeSeriesDataPoint] = []
        totals_by_account: dict[str, Decimal] = {}
        all_account_names: set[str] = set()

        idx = 0
        current = start_date
        while current <= end_date:
            month_key = _get_month_key(current.year, current.month)
            as_of = _next_month(current)

            while idx < len(entry_rows) and entry_rows[idx][0] < as_of:
                _txn_date, acc_id, debit_amount, credit_amount = entry_rows[idx]
                acc_id_str = str(acc_id)
                balances_by_id[acc_id_str] += Decimal(debit_amount) - Decimal(
                    credit_amount,
                )
                idx += 1

            categories: dict[str, Decimal] = {}
            total = Decimal("0")
            for acc_id_str in asset_ids:
                name = asset_name_by_id.get(acc_id_str, "")
                bal = balances_by_id.get(acc_id_str, Decimal("0"))
                categories[name] = bal
                all_account_names.add(name)
                total += bal
                totals_by_account[name] = bal

            data_points.append(
                CategoryTimeSeriesDataPoint(
                    period=month_key,
                    period_label=_get_month_label(current.year, current.month),
                    categories=categories,
                    total=total,
                ),
            )
            current = _next_month(current)

        sorted_accounts = sorted(
            all_account_names,
            key=lambda a: totals_by_account.get(a, Decimal("0")),
            reverse=True,
        )

        return CategoryTimeSeriesResult(
            data_points=data_points,
            categories=sorted_accounts,
            currency="EUR",
            totals_by_category=totals_by_account,
        )

    async def top_expenses(
        self,
        *,
        months: int = 3,
        top_n: int = 10,
        end_month: str | None = None,
        include_drafts: bool = False,
    ) -> TopExpensesResult:
        start_date, end_date = self._calculate_date_range(months, end_month)
        end_exclusive = _next_month(end_date)

        period_label = f"Last {months} month{'s' if months > 1 else ''}"

        stmt = (
            select(
                TransactionModel.id,
                TransactionModel.date,
                AccountModel.name,
                AccountModel.id,
                JournalEntryModel.debit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                AccountModel.account_type == AccountType.EXPENSE.value,
                TransactionModel.date >= start_date,
                TransactionModel.date < end_exclusive,
                JournalEntryModel.debit_amount > 0,
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        rows = (await self._session.execute(stmt)).all()

        spending_by_category: dict[str, Decimal] = defaultdict(Decimal)
        txn_count_by_category: dict[str, int] = defaultdict(int)
        account_ids: dict[str, str] = {}

        for _txn_id, _txn_date, category, account_id, debit_amount in rows:
            amt = Decimal(debit_amount)
            spending_by_category[category] += amt
            txn_count_by_category[category] += 1
            account_ids[category] = str(account_id)

        total_spending = sum(spending_by_category.values(), Decimal("0"))
        sorted_categories = sorted(
            spending_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

        items: list[TopExpenseItem] = []
        for rank, (category, total) in enumerate(sorted_categories, start=1):
            monthly_avg = total / months if months > 0 else total
            pct = (total / total_spending * 100) if total_spending > 0 else Decimal("0")
            items.append(
                TopExpenseItem(
                    rank=rank,
                    category=category,
                    account_id=account_ids.get(category, ""),
                    total_amount=total,
                    monthly_average=monthly_avg.quantize(Decimal("0.01")),
                    percentage_of_total=pct.quantize(Decimal("0.1")),
                    transaction_count=txn_count_by_category.get(category, 0),
                ),
            )

        return TopExpensesResult(
            period_label=period_label,
            items=items,
            total_spending=total_spending,
            currency="EUR",
            months_analyzed=months,
        )

    async def month_comparison(
        self,
        *,
        month: str | None = None,
        include_drafts: bool = False,
    ) -> MonthComparisonResult:
        periods = self._calculate_comparison_periods(month)
        rows = await self._query_comparison_entries(periods, include_drafts)
        aggregated = self._aggregate_comparison_data(rows, periods)
        return self._build_comparison_result(aggregated, periods)

    def _calculate_comparison_periods(
        self,
        month: str | None,
    ) -> dict:
        """Calculate current and previous month date ranges."""
        if month:
            year, m = map(int, month.split("-"))
            current_start = datetime(year, m, 1, tzinfo=timezone.utc)
        else:
            now = utc_now()
            current_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        current_end = _next_month(current_start)
        previous_start = (
            datetime(current_start.year - 1, 12, 1, tzinfo=timezone.utc)
            if current_start.month == 1
            else datetime(
                current_start.year,
                current_start.month - 1,
                1,
                tzinfo=timezone.utc,
            )
        )

        return {
            "current_start": current_start,
            "current_end": current_end,
            "previous_start": previous_start,
            "previous_end": current_start,
            "current_label": f"{month_name[current_start.month]} {current_start.year}",
            "previous_label": (
                f"{month_name[previous_start.month]} {previous_start.year}"
            ),
        }

    async def _query_comparison_entries(
        self,
        periods: dict,
        include_drafts: bool,
    ) -> list:
        """Query income/expense entries for both months."""
        stmt = (
            select(
                TransactionModel.date,
                AccountModel.account_type,
                AccountModel.name,
                JournalEntryModel.debit_amount,
                JournalEntryModel.credit_amount,
            )
            .join(
                JournalEntryModel,
                JournalEntryModel.transaction_id == TransactionModel.id,
            )
            .join(AccountModel, AccountModel.id == JournalEntryModel.account_id)
            .where(
                TransactionModel.user_id == self._user_id,
                AccountModel.user_id == self._user_id,
                TransactionModel.date >= periods["previous_start"],
                TransactionModel.date < periods["current_end"],
                AccountModel.account_type.in_(
                    [AccountType.INCOME.value, AccountType.EXPENSE.value],
                ),
            )
        )
        if not include_drafts:
            stmt = stmt.where(TransactionModel.is_posted.is_(True))

        return list((await self._session.execute(stmt)).all())

    def _aggregate_comparison_data(
        self,
        rows: list,
        periods: dict,
    ) -> dict:
        """Aggregate row data into current/previous totals."""
        current_income = Decimal("0")
        current_spending = Decimal("0")
        current_by_category: dict[str, Decimal] = defaultdict(Decimal)

        previous_income = Decimal("0")
        previous_spending = Decimal("0")
        previous_by_category: dict[str, Decimal] = defaultdict(Decimal)

        current_start = periods["current_start"]
        current_end = periods["current_end"]
        previous_start = periods["previous_start"]
        previous_end = periods["previous_end"]

        for row in rows:
            txn_date, account_type, account_name, debit_amount, credit_amount = row
            txn_date = ensure_tz_aware(txn_date)

            is_current = current_start <= txn_date < current_end
            is_previous = previous_start <= txn_date < previous_end
            if not is_current and not is_previous:
                continue

            if account_type == AccountType.INCOME.value and Decimal(credit_amount) > 0:
                if is_current:
                    current_income += Decimal(credit_amount)
                else:
                    previous_income += Decimal(credit_amount)
                continue

            if account_type == AccountType.EXPENSE.value and Decimal(debit_amount) > 0:
                amt = Decimal(debit_amount)
                if is_current:
                    current_spending += amt
                    current_by_category[account_name] += amt
                else:
                    previous_spending += amt
                    previous_by_category[account_name] += amt

        return {
            "current_income": current_income,
            "current_spending": current_spending,
            "current_by_category": current_by_category,
            "previous_income": previous_income,
            "previous_spending": previous_spending,
            "previous_by_category": previous_by_category,
        }

    def _calculate_pct_change(
        self,
        previous: Decimal,
        current: Decimal,
    ) -> Decimal:
        """Calculate percentage change between two values."""
        if previous == 0:
            return Decimal("0") if current == 0 else Decimal("100")
        return ((current - previous) / abs(previous) * 100).quantize(Decimal("0.1"))

    def _build_category_comparisons(
        self,
        current_by_category: dict[str, Decimal],
        previous_by_category: dict[str, Decimal],
    ) -> list[CategoryComparison]:
        """Build sorted category comparison list."""
        all_categories = set(current_by_category.keys()) | set(
            previous_by_category.keys(),
        )
        comparisons: list[CategoryComparison] = []

        for category in all_categories:
            curr = current_by_category.get(category, Decimal("0"))
            prev = previous_by_category.get(category, Decimal("0"))
            comparisons.append(
                CategoryComparison(
                    category=category,
                    current_amount=curr,
                    previous_amount=prev,
                    change_amount=curr - prev,
                    change_percentage=self._calculate_pct_change(prev, curr),
                ),
            )

        comparisons.sort(key=lambda x: x.current_amount, reverse=True)
        return comparisons

    def _build_comparison_result(
        self,
        data: dict,
        periods: dict,
    ) -> MonthComparisonResult:
        """Build the final comparison result."""
        current_income = data["current_income"]
        current_spending = data["current_spending"]
        previous_income = data["previous_income"]
        previous_spending = data["previous_spending"]

        current_net = current_income - current_spending
        previous_net = previous_income - previous_spending

        return MonthComparisonResult(
            current_month=periods["current_label"],
            previous_month=periods["previous_label"],
            currency="EUR",
            current_income=current_income,
            previous_income=previous_income,
            income_change=current_income - previous_income,
            income_change_percentage=self._calculate_pct_change(
                previous_income,
                current_income,
            ),
            current_spending=current_spending,
            previous_spending=previous_spending,
            spending_change=current_spending - previous_spending,
            spending_change_percentage=self._calculate_pct_change(
                previous_spending,
                current_spending,
            ),
            current_net=current_net,
            previous_net=previous_net,
            net_change=current_net - previous_net,
            net_change_percentage=self._calculate_pct_change(
                previous_net,
                current_net,
            ),
            category_comparisons=self._build_category_comparisons(
                data["current_by_category"],
                data["previous_by_category"],
            ),
        )
