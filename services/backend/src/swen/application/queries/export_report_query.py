"""Export report query - orchestrates data fetching for Excel reports."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.dtos.export_dto import (
    AccountExportDTO,
)
from swen.application.dtos.export_report_dto import (
    AccountBalanceSummary,
    DashboardSummaryDTO,
    ExportReportData,
    MappingExportRowDTO,
    TransactionExportRowDTO,
)
from swen.application.ports.analytics import AnalyticsReadPort
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.integration.repositories import AccountMappingRepository
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory

logger = logging.getLogger(__name__)


class ExportReportQuery:
    """Query to gather all data for Excel report generation."""

    def __init__(
        self,
        analytics_read_port: AnalyticsReadPort,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        mapping_repository: AccountMappingRepository,
    ):
        self._analytics = analytics_read_port
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ExportReportQuery:
        return cls(
            analytics_read_port=factory.analytics_read_port(),
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
        )

    async def execute(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        month: str | None = None,
        include_drafts: bool = True,
    ) -> ExportReportData:
        """Execute query to gather all report data."""
        effective_start, effective_end, period_label = self._resolve_date_range(
            start_date=start_date,
            end_date=end_date,
            days=days,
            month=month,
        )

        summary = await self._build_summary(
            start_date=effective_start,
            end_date=effective_end,
            period_label=period_label,
            month=month,
            include_drafts=include_drafts,
        )

        transactions = await self._fetch_transactions(
            start_date=effective_start,
            end_date=effective_end,
            include_drafts=include_drafts,
        )

        accounts = await self._fetch_accounts()
        mappings = await self._fetch_mappings()

        return ExportReportData(
            summary=summary,
            transactions=transactions,
            accounts=accounts,
            mappings=mappings,
        )

    def _resolve_date_range(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        days: int | None,
        month: str | None,
    ) -> tuple[date | None, date | None, str]:
        """Resolve the effective date range and period label."""
        today = date.today()

        if start_date and end_date:
            label = (
                f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
            )
            return start_date, end_date, label

        if days:
            effective_start = today - timedelta(days=days)
            label = f"Last {days} days"
            return effective_start, today, label

        if month:
            year, month_num = map(int, month.split("-"))
            effective_start = date(year, month_num, 1)
            if month_num == 12:
                effective_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                effective_end = date(year, month_num + 1, 1) - timedelta(days=1)
            label = effective_start.strftime("%B %Y")
            return effective_start, effective_end, label

        return None, None, "All Time"

    async def _build_summary(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        period_label: str,
        month: str | None,
        include_drafts: bool,
    ) -> DashboardSummaryDTO:
        """Build the dashboard summary from analytics data."""
        now = utc_now()
        spending = await self._analytics.spending_breakdown(
            month=month,
            days=self._calculate_days(start_date, end_date) if start_date else None,
            include_drafts=include_drafts,
        )

        income = await self._analytics.income_breakdown(
            month=month,
            days=self._calculate_days(start_date, end_date) if start_date else None,
            include_drafts=include_drafts,
        )

        net_worth_result = await self._analytics.net_worth_over_time(
            months=6,
            include_drafts=include_drafts,
        )
        current_net_worth = (
            net_worth_result.data_points[-1].value
            if net_worth_result.data_points
            else Decimal("0")
        )

        month_comparison = None
        if month or (start_date and end_date):
            try:
                month_comparison = await self._analytics.month_comparison(
                    month=month,
                    include_drafts=include_drafts,
                )
            except Exception:
                logger.debug(
                    "Month comparison not available for date range",
                    exc_info=True,
                )

        account_balances = await self._fetch_account_balances(include_drafts)

        total_income = income.total
        total_expenses = spending.total
        net_income = total_income - total_expenses
        savings_rate = (
            (net_income / total_income * 100) if total_income > 0 else Decimal("0")
        )

        all_transactions = await self._transaction_repo.find_all()
        posted = [t for t in all_transactions if t.is_posted]

        return DashboardSummaryDTO(
            report_title="SWEN Financial Report",
            period_label=period_label,
            start_date=start_date,
            end_date=end_date,
            generated_at=now,
            currency="EUR",
            total_income=total_income,
            total_expenses=total_expenses,
            net_income=net_income,
            savings_rate=savings_rate,
            net_worth=current_net_worth,
            account_balances=account_balances,
            top_expenses=spending.items[:10],
            month_comparison=month_comparison,
            net_worth_trend=net_worth_result.data_points,
            transaction_count=len(all_transactions),
            posted_count=len(posted),
            draft_count=len(all_transactions) - len(posted),
        )

    def _calculate_days(self, start_date: date | None, end_date: date | None) -> int:
        if not start_date or not end_date:
            return 0
        return (end_date - start_date).days + 1

    async def _fetch_account_balances(
        self,
        include_drafts: bool,
    ) -> list[AccountBalanceSummary]:
        balance_history = await self._analytics.balance_history_over_time(
            months=1,
            include_drafts=include_drafts,
        )

        if not balance_history.data_points:
            return []

        latest = balance_history.data_points[-1]
        balances = []

        for account_name, balance in sorted(
            latest.categories.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            balances.append(
                AccountBalanceSummary(
                    account_name=account_name,
                    account_number="",
                    balance=balance,
                    currency=balance_history.currency,
                ),
            )

        return balances

    async def _fetch_transactions(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        include_drafts: bool,
    ) -> list[TransactionExportRowDTO]:
        if include_drafts:
            all_txns = await self._transaction_repo.find_all()
        else:
            all_txns = await self._transaction_repo.find_posted_transactions()

        if start_date:
            all_txns = [t for t in all_txns if t.date.date() >= start_date]
        if end_date:
            all_txns = [t for t in all_txns if t.date.date() <= end_date]

        result = []
        for txn in sorted(all_txns, key=lambda t: t.date, reverse=True):
            row = self._transaction_to_export_row(txn)
            result.append(row)

        return result

    def _transaction_to_export_row(self, txn) -> TransactionExportRowDTO:
        amount = Decimal("0")
        currency = "EUR"
        debit_account = ""
        credit_account = ""

        for entry in txn.entries:
            if entry.is_debit():
                debit_account = f"{entry.account.account_number} - {entry.account.name}"
                amount = entry.debit.amount
                currency = entry.debit.currency.code
            else:
                credit_account = (
                    f"{entry.account.account_number} - {entry.account.name}"
                )

        try:
            meta = txn.metadata
        except Exception:
            meta = None

        original_purpose = meta.original_purpose if meta else ""
        bank_reference = meta.bank_reference if meta else ""

        ai_suggested = ""
        ai_confidence = None
        ai_accepted = None
        if meta and meta.ai_resolution:
            ai_suggested = meta.ai_resolution.suggested_counter_account_name or ""
            ai_confidence = meta.ai_resolution.confidence
            ai_accepted = meta.ai_resolution.suggestion_accepted

        return TransactionExportRowDTO(
            id=str(txn.id),
            date=txn.date.strftime("%Y-%m-%d"),
            description=txn.description,
            counterparty=txn.counterparty or "",
            amount=float(amount),
            currency=currency,
            debit_account=debit_account,
            credit_account=credit_account,
            status="posted" if txn.is_posted else "draft",
            source=txn.source.value,
            source_iban=txn.source_iban or "",
            counterparty_iban=txn.counterparty_iban or "",
            is_internal_transfer=txn.is_internal_transfer,
            original_purpose=original_purpose or "",
            bank_reference=bank_reference or "",
            ai_suggested_account=ai_suggested,
            ai_confidence=ai_confidence,
            ai_accepted=ai_accepted,
        )

    async def _fetch_accounts(self) -> list[AccountExportDTO]:
        all_accounts = await self._account_repo.find_all()
        return [AccountExportDTO.from_account(a) for a in all_accounts]

    async def _fetch_mappings(self) -> list[MappingExportRowDTO]:
        all_mappings = await self._mapping_repo.find_all()

        all_accounts = await self._account_repo.find_all()
        account_lookup = {
            acc.id: (acc.account_number, acc.name) for acc in all_accounts
        }

        result = []
        for mapping in all_mappings:
            account_info = account_lookup.get(mapping.accounting_account_id)
            if account_info:
                account_number, account_name = account_info
            else:
                account_number = ""
                account_name = str(mapping.accounting_account_id)

            result.append(
                MappingExportRowDTO(
                    iban=mapping.iban,
                    bank_account_name=mapping.account_name,
                    accounting_account_name=account_name,
                    accounting_account_number=account_number,
                    created_at=(
                        mapping.created_at.isoformat() if mapping.created_at else ""
                    ),
                ),
            )

        return result
