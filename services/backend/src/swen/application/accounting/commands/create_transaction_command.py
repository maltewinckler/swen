"""Create transactions from explicit journal entries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.accounting.dtos.transactions_dto import (
    TransactionDTO,
    TransactionEntryDTO,
    TransactionToCreateDTO,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.value_objects import (
    Money,
    TransactionMetadata,
    TransactionSource,
)
from swen.domain.shared.current_user import CurrentUser
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class CreateTransactionCommand:
    """Create a transaction from application-layer DTO."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        current_user: CurrentUser,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._current_user = current_user

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> CreateTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            current_user=factory.current_user,
        )

    async def execute(self, dto: TransactionToCreateDTO) -> TransactionDTO:
        """Execute the create transaction use case."""
        accounts = await self._load_accounts(dto.entries)

        transaction = Transaction(
            description=dto.description,
            user_id=self._current_user.user_id,
            date=dto.date or utc_now(),
            counterparty=dto.counterparty,
            counterparty_iban=dto.counterparty_iban,
            source=TransactionSource(dto.source),
            source_iban=dto.source_iban,
            is_internal_transfer=dto.is_internal_transfer,
        )

        metadata = TransactionMetadata(
            source=TransactionSource(dto.source),
            is_manual_entry=dto.is_manual_entry,
        )
        transaction.set_metadata(metadata)

        self._add_entries(transaction, dto.entries, accounts)

        if dto.auto_post:
            transaction.post()

        await self._transaction_repo.save(transaction)

        return self._to_dto(transaction)

    async def _load_accounts(
        self,
        entries: list[TransactionEntryDTO],
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
        entries: list[TransactionEntryDTO],
        accounts: dict[UUID, Account],
    ) -> None:
        for entry in entries:
            account = accounts[entry.account_id]
            if entry.debit > 0:
                money = Money(entry.debit, account.default_currency)
                transaction.add_debit(account, money)
            elif entry.credit > 0:
                money = Money(entry.credit, account.default_currency)
                transaction.add_credit(account, money)

    def _to_dto(self, transaction: Transaction) -> TransactionDTO:
        return TransactionDTO.from_transaction(transaction)
