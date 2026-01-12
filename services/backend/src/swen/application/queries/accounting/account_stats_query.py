"""Account statistics query - retrieve detailed stats for a single account."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.dtos.accounting import AccountStatsResult
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import AccountBalanceService

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class AccountStatsQuery:
    """Query to get comprehensive statistics for a single account.

    This query calculates:
    - Current balance (with optional draft inclusion)
    - Transaction counts (total, posted, draft)
    - Flow statistics (debits, credits, net flow)
    - Activity timestamps (first/last transaction dates)
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        balance_service: AccountBalanceService,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._balance_service = balance_service

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> AccountStatsQuery:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            balance_service=AccountBalanceService(),
        )

    async def execute(
        self,
        account_id: UUID,
        days: Optional[int] = None,
        include_drafts: bool = True,
    ) -> AccountStatsResult:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id=account_id)

        period_end = datetime.now(timezone.utc).date()
        period_start: Optional[date] = None
        if days is not None:
            period_start = period_end - timedelta(days=days)

        all_transactions = await self._transaction_repo.find_all()
        account_transactions = [
            t for t in all_transactions if t.involves_account(account)
        ]

        if period_start is not None:
            period_transactions = [
                t for t in account_transactions if t.date.date() >= period_start
            ]
        else:
            period_transactions = account_transactions

        if include_drafts:
            flow_transactions = period_transactions
        else:
            flow_transactions = [t for t in period_transactions if t.is_posted]

        balance_transactions = (
            account_transactions
            if include_drafts
            else [t for t in account_transactions if t.is_posted]
        )
        balance = self._balance_service.calculate_balance(
            account=account,
            transactions=balance_transactions,
            include_drafts=include_drafts,
        )

        total_count = len(period_transactions)
        posted_count = sum(1 for t in period_transactions if t.is_posted)
        draft_count = total_count - posted_count

        total_debits = Decimal("0")
        total_credits = Decimal("0")

        for txn in flow_transactions:
            for entry in txn.entries:
                if entry.account.id == account.id:
                    total_debits += entry.debit.amount
                    total_credits += entry.credit.amount

        net_flow = total_debits - total_credits

        first_transaction_date: Optional[date] = None
        last_transaction_date: Optional[date] = None

        if account_transactions:
            sorted_txns = sorted(account_transactions, key=lambda t: t.date)
            first_transaction_date = sorted_txns[0].date.date()
            last_transaction_date = sorted_txns[-1].date.date()

        return AccountStatsResult(
            account_id=account.id,
            account_name=account.name,
            account_number=account.account_number,
            account_type=account.account_type.value,
            currency=account.default_currency.code,
            balance=balance.amount,
            balance_includes_drafts=include_drafts,
            transaction_count=total_count,
            posted_count=posted_count,
            draft_count=draft_count,
            total_debits=total_debits,
            total_credits=total_credits,
            net_flow=net_flow,
            first_transaction_date=first_transaction_date,
            last_transaction_date=last_transaction_date,
            period_days=days,
            period_start=period_start,
            period_end=period_end,
        )
