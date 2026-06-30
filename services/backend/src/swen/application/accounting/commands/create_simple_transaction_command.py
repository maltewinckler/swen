"""Convenience wrapper for creating simple two-entry transactions."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.accounting.commands.create_transaction_command import (
    CreateTransactionCommand,
)
from swen.application.accounting.dtos.transactions_dto import (
    JournalEntryToCreateDTO,
    SimpleTransactionToCreateDTO,
    TransactionDTO,
    TransactionToCreateDTO,
)
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    InvalidAccountTypeError,
)
from swen.domain.accounting.value_objects import TransactionSource
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.shared.current_user import CurrentUser


class CreateSimpleTransactionCommand:
    """Create a two-entry transaction from minimal inputs."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        current_user: CurrentUser,
    ):
        self._account_repo = account_repository
        self._current_user = current_user

        # Compose the underlying entry-based command
        self._create_command = CreateTransactionCommand(
            transaction_repository=transaction_repository,
            account_repository=account_repository,
            current_user=current_user,
        )

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> CreateSimpleTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            current_user=factory.current_user,
        )

    async def execute(self, dto: SimpleTransactionToCreateDTO) -> TransactionDTO:
        if dto.amount == Decimal("0"):
            msg = "Amount must be non-zero"
            raise ValidationError(msg)

        # Look up accounts by account number
        payment_account = await self._resolve_payment_account(dto)
        counter_account = await self._resolve_counter_account(dto)

        dto_entries = self._create_journal_entry_dtos(
            payment_account, counter_account, dto.amount
        )

        general_transaction_to_create_dto = TransactionToCreateDTO(
            description=dto.description,
            entries=list(dto_entries),
            counterparty=dto.counterparty,
            date=dto.date,
            source=TransactionSource.MANUAL.value,
            is_manual_entry=True,
            auto_post=dto.auto_post,
        )
        return await self._create_command.execute(general_transaction_to_create_dto)

    async def _resolve_account_by_number(
        self,
        account_number: str,
    ) -> Account:
        account = await self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise AccountNotFoundError(account_name=account_number)
        return account

    async def _resolve_payment_account(
        self, dto: SimpleTransactionToCreateDTO
    ) -> Account:
        a = await self._resolve_account_by_number(dto.payment_account)
        if not (a.is_asset_account() or a.is_liability_account()):
            raise InvalidAccountTypeError(a.account_type.value, ["asset", "liability"])
        return a

    async def _resolve_counter_account(
        self, dto: SimpleTransactionToCreateDTO
    ) -> Account:
        a = await self._resolve_account_by_number(dto.counter_account)
        is_expense = dto.amount < 0

        violation_1 = is_expense and not a.is_expense_account()
        violation_2 = not is_expense and not a.is_income_account()
        if violation_1 or violation_2:
            raise InvalidAccountTypeError(a.account_type.value, ["income", "expense"])
        return a

    def _create_journal_entry_dtos(
        self,
        payment_account: Account,
        counter_account: Account,
        amount: Decimal,
    ) -> tuple[JournalEntryToCreateDTO, JournalEntryToCreateDTO]:
        """Build two journal entries for a simple transaction.

        Debit/Credit rules:
        - **Expense** (negative amount): Debit *counter_account* (expense),
          Credit *payment_account* (asset/liability).
        - **Income** (positive amount): Debit *payment_account* (asset/liability),
          Credit *counter_account* (income).

        Args:
            payment_account: The asset or liability account from which funds
                flow (the "checking", "credit card", etc.).
            counter_account: The income or expense account paired with the
                payment account.
            amount: Positive for income, negative for expense.

        Returns
        -------
            A two-element tuple of ``JournalEntryToCreateDTO`` where the first
            element is the debit entry and the second is the credit entry.
        """
        payment_acc_id = payment_account.id
        counter_acc_id = counter_account.id
        is_expense = amount < 0
        abs_amount = abs(amount)

        if is_expense:
            return (
                JournalEntryToCreateDTO(account_id=counter_acc_id, debit=abs_amount),
                JournalEntryToCreateDTO(account_id=payment_acc_id, credit=abs_amount),
            )
        return (
            JournalEntryToCreateDTO(account_id=payment_acc_id, debit=abs_amount),
            JournalEntryToCreateDTO(account_id=counter_acc_id, credit=abs_amount),
        )
