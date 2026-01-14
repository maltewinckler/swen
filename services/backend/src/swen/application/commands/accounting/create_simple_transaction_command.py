"""Convenience wrapper for creating simple two-entry transactions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from swen.application.commands.accounting.create_transaction_command import (
    CreateTransactionCommand,
)
from swen.application.ports.identity import CurrentUser
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import (
    TransactionDirection,
    TransactionEntryService,
)
from swen.domain.accounting.value_objects import (
    JournalEntryInput,
    Money,
    TransactionSource,
)
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class ResolvedAccounts:
    """Result of account resolution for simple transactions."""

    asset_account: Account
    category_account: Account


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
        asset_account_hint: Optional[str] = None,
        category_account_hint: Optional[str] = None,
        counterparty: Optional[str] = None,
        date: Optional[datetime] = None,
        auto_post: bool = False,
    ) -> Transaction:
        if amount == Decimal("0"):
            msg = "Amount must be non-zero"
            raise ValidationError(msg)

        is_expense = amount < 0
        abs_amount = abs(amount)

        # Resolve accounts from hints or defaults
        resolved = await self._resolve_accounts(
            asset_hint=asset_account_hint,
            category_hint=category_account_hint,
            is_expense=is_expense,
        )

        # Use domain service for entry direction rules
        direction = (
            TransactionDirection.EXPENSE if is_expense else TransactionDirection.INCOME
        )
        money = Money(abs_amount, resolved.asset_account.default_currency)

        entry_specs = TransactionEntryService.build_simple_entries(
            payment_account=resolved.asset_account,
            category_account=resolved.category_account,
            amount=money,
            direction=direction,
        )

        # Convert EntrySpec to JournalEntryInput for CreateTransactionCommand
        entries = []
        for spec in entry_specs:
            if spec.is_debit:
                entries.append(
                    JournalEntryInput.debit_entry(spec.account.id, spec.amount.amount),
                )
            else:
                entries.append(
                    JournalEntryInput.credit_entry(spec.account.id, spec.amount.amount),
                )

        # Delegate to the entry-based command
        return await self._create_command.execute(
            description=description,
            entries=entries,
            counterparty=counterparty,
            date=date,
            source=TransactionSource.MANUAL,
            is_manual_entry=True,
            auto_post=auto_post,
        )

    async def _resolve_accounts(
        self,
        asset_hint: Optional[str],
        category_hint: Optional[str],
        is_expense: bool,
    ) -> ResolvedAccounts:
        asset_account = await self._resolve_payment_account(asset_hint)
        if not asset_account:
            raise AccountNotFoundError(
                account_name=asset_hint or "default payment account",
            )

        category_type = "expense" if is_expense else "income"
        category_account = await self._resolve_category_account(
            category_hint,
            category_type,
        )
        if not category_account:
            raise AccountNotFoundError(
                account_name=category_hint or f"default {category_type}",
            )

        return ResolvedAccounts(
            asset_account=asset_account,
            category_account=category_account,
        )

    async def _resolve_payment_account(
        self,
        hint: Optional[str],
    ) -> Optional[Account]:
        payment_types = {AccountType.ASSET, AccountType.LIABILITY}

        if hint:
            account = await self._account_repo.find_by_account_number(hint)
            if account and account.account_type in payment_types:
                return account

            # Try by name
            all_accounts = await self._account_repo.find_all()
            for acc in all_accounts:
                if (
                    acc.account_type in payment_types
                    and acc.name.lower() == hint.lower()
                ):
                    return acc

        # Default to first active asset account (prefer assets over liabilities)
        all_accounts = await self._account_repo.find_all()
        for acc in all_accounts:
            if acc.account_type == AccountType.ASSET and acc.is_active:
                return acc

        return None

    async def _resolve_category_account(
        self,
        hint: Optional[str],
        category_type: str,
    ) -> Optional[Account]:
        target_type = (
            AccountType.EXPENSE if category_type == "expense" else AccountType.INCOME
        )

        if hint:
            account = await self._account_repo.find_by_account_number(hint)
            if account and account.account_type == target_type:
                return account

        # Find default category (prefer "sonstig/other" accounts)
        all_accounts = await self._account_repo.find_all()
        candidates = [
            acc
            for acc in all_accounts
            if acc.account_type == target_type and acc.is_active
        ]

        if not candidates:
            return None

        # Prefer "sonstig" or "other" accounts as fallback
        for acc in candidates:
            name_lower = acc.name.lower()
            if "sonstig" in name_lower or "other" in name_lower:
                return acc

        return candidates[0]
