"""List transactions with optional filters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.dtos.accounting import (
    TransactionDetailDTO,
    TransactionListItemDTO,
    TransactionListResultDTO,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class TransactionListResult:
    """Result of listing transactions (returns domain objects)."""

    transactions: list[Transaction]
    total_count: int
    draft_count: int
    posted_count: int


class ListTransactionsQuery:
    """List transactions with date/status/account filters."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListTransactionsQuery:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
        )

    async def execute(  # NOQA: PLR0913
        self,
        days: int = 30,
        limit: int = 50,
        status_filter: Optional[str] = None,
        iban_filter: Optional[str] = None,
        show_drafts: bool = True,
        exclude_transfers: Optional[bool] = None,
    ) -> TransactionListResult:
        now = utc_now()
        start_date = (now - timedelta(days=days)).isoformat()

        status = status_filter
        if status is None and not show_drafts:
            status = "posted"

        account_id = None
        if iban_filter:
            account = await self._account_repo.find_by_account_number(iban_filter)
            if account:
                account_id = account.id
            else:
                counts = await self._transaction_repo.count_by_status()
                return TransactionListResult(
                    transactions=[],
                    total_count=counts["total"],
                    draft_count=counts["draft"],
                    posted_count=counts["posted"],
                )

        should_exclude_transfers = exclude_transfers
        if should_exclude_transfers is None:
            should_exclude_transfers = iban_filter is None

        filtered = await self._transaction_repo.find_with_filters(
            start_date=start_date,
            status=status,
            account_id=account_id,
            exclude_internal_transfers=should_exclude_transfers,
            limit=limit,
        )

        counts = await self._transaction_repo.count_by_status()

        return TransactionListResult(
            transactions=filtered,
            total_count=counts["total"],
            draft_count=counts["draft"],
            posted_count=counts["posted"],
        )

    async def find_by_id(
        self,
        transaction_id: UUID,
    ) -> Optional[Transaction]:
        return await self._transaction_repo.find_by_id(transaction_id)

    async def find_by_partial_id(
        self,
        partial_id: str,
    ) -> Optional[Transaction]:
        posted = await self._transaction_repo.find_posted_transactions()
        drafts = await self._transaction_repo.find_draft_transactions()

        for txn in posted + drafts:
            if str(txn.id).startswith(partial_id):
                return txn
        return None

    async def find_by_id_or_partial(
        self,
        transaction_id: str,
    ) -> Optional[Transaction]:
        try:
            txn_uuid = UUID(transaction_id)
            return await self.find_by_id(txn_uuid)
        except ValueError:
            return await self.find_by_partial_id(transaction_id)

    async def get_transaction_list(  # NOQA: PLR0913
        self,
        days: int = 30,
        limit: int = 50,
        status_filter: Optional[str] = None,
        iban_filter: Optional[str] = None,
        show_drafts: bool = True,
        exclude_transfers: Optional[bool] = None,
    ) -> TransactionListResultDTO:
        result = await self.execute(
            days=days,
            limit=limit,
            status_filter=status_filter,
            iban_filter=iban_filter,
            show_drafts=show_drafts,
            exclude_transfers=exclude_transfers,
        )

        items = [
            TransactionListItemDTO.from_transaction(txn) for txn in result.transactions
        ]

        return TransactionListResultDTO(
            transactions=items,
            total_count=result.total_count,
        )

    async def get_transaction_detail(
        self,
        transaction_id: UUID,
    ) -> Optional[TransactionDetailDTO]:
        txn = await self.find_by_id(transaction_id)
        if not txn:
            return None
        return TransactionDetailDTO.from_transaction(txn)

    async def get_transaction_detail_by_partial_id(
        self,
        partial_id: str,
    ) -> Optional[TransactionDetailDTO]:
        txn = await self.find_by_partial_id(partial_id)
        if not txn:
            return None
        return TransactionDetailDTO.from_transaction(txn)

    async def get_detail_by_id_or_partial(
        self,
        transaction_id: str,
    ) -> Optional[TransactionDetailDTO]:
        txn = await self.find_by_id_or_partial(transaction_id)
        if not txn:
            return None
        return TransactionDetailDTO.from_transaction(txn)
