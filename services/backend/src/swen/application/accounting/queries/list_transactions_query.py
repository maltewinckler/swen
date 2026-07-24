"""List transactions with optional filters and pagination."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.accounting.dtos import (
    TransactionDTO,
    TransactionListFilterDTO,
    TransactionListItemDTO,
    TransactionListResultDTO,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.accounting.value_objects import TransactionFilters
from swen.domain.shared.value_objects import Pagination

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


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

    async def execute(
        self,
        filters: TransactionListFilterDTO,
    ) -> TransactionListResultDTO:
        status = filters.status_filter
        if status is None and not filters.show_drafts:
            status = "posted"

        account_id = None
        if filters.iban_filter:
            account = await self._account_repo.find_by_account_number(
                filters.iban_filter
            )
            if account:
                account_id = account.id
            else:
                counts = await self._transaction_repo.count_by_status()
                return TransactionListResultDTO(
                    transactions=[],
                    total=counts["total"],
                    filtered_count=0,
                    draft_count=counts["draft"],
                    posted_count=counts["posted"],
                    page=filters.page,
                    page_size=filters.page_size,
                )

        should_exclude_transfers = filters.exclude_transfers
        if should_exclude_transfers is None:
            should_exclude_transfers = filters.iban_filter is None

        txn_filters = TransactionFilters(
            status=status,
            account_id=account_id,
            exclude_internal_transfers=should_exclude_transfers,
        )
        pagination = Pagination(page=filters.page, page_size=filters.page_size)

        filtered = await self._transaction_repo.find_with_filters(
            filters=txn_filters,
            pagination=pagination,
        )
        filtered_count = await self._transaction_repo.count_with_filters(txn_filters)
        counts = await self._transaction_repo.count_by_status()

        return TransactionListResultDTO(
            transactions=[
                TransactionListItemDTO.from_transaction(txn) for txn in filtered
            ],
            total=counts["total"],
            filtered_count=filtered_count,
            draft_count=counts["draft"],
            posted_count=counts["posted"],
            page=filters.page,
            page_size=filters.page_size,
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

    async def get_transaction_detail(
        self,
        transaction_id: UUID,
    ) -> Optional[TransactionDTO]:
        txn = await self.find_by_id(transaction_id)
        if not txn:
            return None
        return TransactionDTO.from_transaction(txn)

    async def get_transaction_detail_by_partial_id(
        self,
        partial_id: str,
    ) -> Optional[TransactionDTO]:
        txn = await self.find_by_partial_id(partial_id)
        if not txn:
            return None
        return TransactionDTO.from_transaction(txn)

    async def get_detail_by_id_or_partial(
        self,
        transaction_id: str,
    ) -> Optional[TransactionDTO]:
        txn = await self.find_by_id_or_partial(transaction_id)
        if not txn:
            return None
        return TransactionDTO.from_transaction(txn)
