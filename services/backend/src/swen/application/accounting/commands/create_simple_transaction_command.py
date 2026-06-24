"""Convenience wrapper for creating simple two-entry transactions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from swen.application.accounting.commands.create_transaction_command import (
    CreateTransactionCommand,
)
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.services import TransactionEntryService
from swen.domain.accounting.value_objects import Money, TransactionSource
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.aggregates import Transaction
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

    async def execute(  # NOQA: PLR0913
        self,
        description: str,
        amount: Decimal,
        payment_account_number: str,
        counter_account_number: str,
        counterparty: Optional[str] = None,
        date: Optional[datetime] = None,
        auto_post: bool = False,
    ) -> Transaction:
        if amount == Decimal("0"):
            msg = "Amount must be non-zero"
            raise ValidationError(msg)

        is_expense = amount < 0
        abs_amount = abs(amount)

        # Look up accounts by account number
        payment_account = await self._resolve_account_number(payment_account_number)
        counter_account = await self._resolve_account_number(counter_account_number)

        # Use domain service for entry direction rules
        money = Money(abs_amount, payment_account.default_currency)

        entries = TransactionEntryService.build_simple_entries(
            payment_account=payment_account,
            category_account=counter_account,
            amount=money,
            is_expense=is_expense,
        )

        # Delegate to the entry-based command
        return await self._create_command.execute(
            description=description,
            entries=list(entries),  # build_simple_entries has always 2 entries
            counterparty=counterparty,
            date=date,
            source=TransactionSource.MANUAL,
            is_manual_entry=True,
            auto_post=auto_post,
        )

    async def _resolve_account_number(
        self,
        account_number: str,
    ) -> Account:
        account = await self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise AccountNotFoundError(account_name=account_number)
        return account
