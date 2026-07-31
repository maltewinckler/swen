"""Coordinator for editing existing accounting transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.accounting.dtos.transactions_dto import (
    JournalEntryToCreateDTO,
    TransactionDTO,
    TransactionToEditDTO,
)
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import JournalEntry
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    TransactionNotFoundError,
)
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.accounting.services import TransactionEditService
from swen.domain.accounting.value_objects import Money

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.entities import Account


class EditTransactionCommand:
    """Apply edits to a transaction and persist the result."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        uow: UnitOfWork,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> EditTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            uow=factory.unit_of_work(),
        )

    async def _update_with_new_entries(
        self,
        transaction: Transaction,
        dto_entries: list[JournalEntryToCreateDTO],
    ) -> None:
        """Replace transaction entries."""
        account_ids = {entry.account_id for entry in dto_entries}
        accounts = await self._load_accounts(account_ids)

        journal_entries: list[JournalEntry] = []
        for dto in dto_entries:
            account = accounts[dto.account_id]
            if dto.debit > 0:
                money = Money(dto.debit, account.default_currency)
                journal_entries.append(
                    JournalEntry(account=account, debit=money, credit=None),
                )
            elif dto.credit > 0:
                money = Money(dto.credit, account.default_currency)
                journal_entries.append(
                    JournalEntry(account=account, debit=None, credit=money),
                )

        TransactionEditService.replace_entries(transaction, journal_entries)

    async def _update_with_new_counter_account(
        self,
        transaction: Transaction,
        counter_account_id: UUID,
    ):
        accounts = await self._load_accounts({counter_account_id})
        counter_account = accounts[counter_account_id]
        TransactionEditService.change_counter_account(transaction, counter_account)

    async def execute(
        self,
        dto: TransactionToEditDTO,
    ) -> TransactionDTO:
        # Validate mutually exclusive parameters
        if dto.entries is not None and dto.counter_account_id is not None:
            msg = (
                "Cannot specify both 'entries' and 'counter_account_id'. "
                "Use 'entries' for full entry replacement or "
                "'counter_account_id' for simple counter-account swap."
            )
            raise ValueError(msg)

        async with self._uow:
            transaction = await self._load_transaction(dto.transaction_id)
            was_posted = self._unpost_if_needed(transaction)  # to be able to edit

            if dto.entries is not None:
                await self._update_with_new_entries(transaction, dto.entries)
            elif dto.counter_account_id is not None:
                await self._update_with_new_counter_account(
                    transaction, dto.counter_account_id
                )

            if dto.description is not None:
                transaction.update_description(dto.description)
            if dto.counterparty is not None:
                transaction.update_counterparty(dto.counterparty)
            if dto.metadata is not None:
                TransactionEditService.update_metadata(transaction, dto.metadata)

            # Repost if requested and was originally posted
            if dto.repost and was_posted:
                transaction.post()

            # Persist changes
            await self._transaction_repo.save(transaction)
            return TransactionDTO.from_transaction(transaction)

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
