"""Create transactions from explicit journal entries."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.context.user_context import UserContext
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.value_objects import (
    JournalEntryInput,
    Money,
    TransactionMetadata,
    TransactionSource,
)
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class CreateTransactionCommand:
    """Create a transaction from balanced journal entries."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        user_context: UserContext,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._user_context = user_context

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> CreateTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            user_context=factory.user_context,
        )

    async def execute(  # NOQA: PLR0913
        self,
        description: str,
        entries: list[JournalEntryInput],
        counterparty: Optional[str] = None,
        counterparty_iban: Optional[str] = None,
        date: Optional[datetime] = None,
        source: TransactionSource = TransactionSource.MANUAL,
        source_iban: Optional[str] = None,
        is_internal_transfer: bool = False,
        is_manual_entry: bool = False,
        auto_post: bool = False,
    ) -> Transaction:
        accounts = await self._load_accounts(entries)

        # Create transaction aggregate with promoted fields
        transaction = Transaction(
            description=description,
            user_id=self._user_context.user_id,
            date=date or utc_now(),
            counterparty=counterparty,
            counterparty_iban=counterparty_iban,
            source=source,
            source_iban=source_iban,
            is_internal_transfer=is_internal_transfer,
        )

        # Set metadata with additional tracking info
        metadata = TransactionMetadata(
            source=source,
            is_manual_entry=is_manual_entry,
        )
        transaction.set_metadata(metadata)

        # Add entries to transaction
        self._add_entries(transaction, entries, accounts)

        # Post if requested (validates balance)
        if auto_post:
            transaction.post()

        # Persist
        await self._transaction_repo.save(transaction)

        return transaction

    async def _load_accounts(
        self,
        entries: list[JournalEntryInput],
    ) -> dict[UUID, Account]:
        account_ids = {entry.account_id for entry in entries}
        accounts: dict[UUID, Account] = {}

        for account_id in account_ids:
            account = await self._account_repo.find_by_id(account_id)
            if not account:
                raise AccountNotFoundError(account_id=account_id)
            accounts[account_id] = account

        return accounts

    def _add_entries(
        self,
        transaction: Transaction,
        entries: list[JournalEntryInput],
        accounts: dict[UUID, Account],
    ):
        for entry_input in entries:
            account = accounts[entry_input.account_id]
            money = Money(entry_input.amount, account.default_currency)

            if entry_input.is_debit:
                transaction.add_debit(account, money)
            else:
                transaction.add_credit(account, money)
