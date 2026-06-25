"""Coordinator for editing existing accounting transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    TransactionNotFoundError,
)
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.accounting.services import TransactionEditService
from swen.domain.accounting.value_objects import JournalEntryInput

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.entities import Account


class EditTransactionCommand:
    """Apply edits to a transaction and persist the result."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> EditTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
        )

    async def _update_with_new_entries(
        self,
        transaction: Transaction,
        entries: list[JournalEntryInput],
    ):
        account_ids = {entry.account_id for entry in entries}
        accounts = await self._load_accounts(account_ids)
        TransactionEditService.replace_entries(transaction, entries, accounts)

    async def _update_with_new_counter_account(
        self,
        transaction: Transaction,
        counter_account_id: UUID,
    ):
        accounts = await self._load_accounts({counter_account_id})
        counter_account = accounts[counter_account_id]
        TransactionEditService.change_counter_account(transaction, counter_account)

    async def execute(  # NOQA: PLR0913
        self,
        transaction_id: UUID,
        entries: Optional[list[JournalEntryInput]] = None,
        counter_account_id: Optional[UUID] = None,
        description: Optional[str] = None,
        counterparty: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        repost: bool = False,
    ) -> Transaction:
        # Validate mutually exclusive parameters
        if entries is not None and counter_account_id is not None:
            msg = (
                "Cannot specify both 'entries' and 'counter_account_id'. "
                "Use 'entries' for full entry replacement or "
                "'counter_account_id' for simple counter-account swap."
            )
            raise ValueError(msg)

        transaction = await self._load_transaction(transaction_id)
        was_posted = self._unpost_if_needed(transaction)  # to be able to edit

        if entries is not None:
            await self._update_with_new_entries(transaction, entries)
        elif counter_account_id is not None:
            await self._update_with_new_counter_account(transaction, counter_account_id)

        if description is not None:
            transaction.update_description(description)
        if counterparty is not None:
            transaction.update_counterparty(counterparty)
        if metadata is not None:
            TransactionEditService.update_metadata(transaction, metadata)

        # Repost if requested and was originally posted
        if repost and was_posted:
            transaction.post()

        # Persist changes
        await self._transaction_repo.save(transaction)
        return transaction

    async def _load_transaction(self, transaction_id: UUID) -> Transaction:
        transaction = await self._transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError(transaction_id)
        return transaction

    def _unpost_if_needed(self, transaction: Transaction) -> bool:
        was_posted = transaction.is_posted
        if was_posted:
            transaction.unpost()
        return was_posted

    async def _load_accounts(
        self,
        account_ids: set[UUID],
    ) -> dict[UUID, Account]:
        accounts: dict[UUID, Account] = {}

        for account_id in account_ids:
            account = await self._account_repo.find_by_id(account_id)
            if not account:
                raise AccountNotFoundError(account_id=account_id)
            accounts[account_id] = account

        return accounts
