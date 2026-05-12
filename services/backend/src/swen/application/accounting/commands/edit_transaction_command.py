"""Coordinator for editing existing accounting transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    TransactionNotFoundError,
)
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.accounting.services import (
    CATEGORY_ACCOUNT_TYPES,
    PAYMENT_ACCOUNT_TYPES,
    TransactionEntryService,
)
from swen.domain.accounting.value_objects import JournalEntryInput, MetadataKeys, Money
from swen.domain.shared.exceptions import BusinessRuleViolation, ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


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

    async def execute(  # NOQA: PLR0913
        self,
        transaction_id: UUID,
        entries: Optional[list[JournalEntryInput]] = None,
        category_account_id: Optional[UUID] = None,
        description: Optional[str] = None,
        counterparty: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        repost: bool = False,
    ) -> Transaction:
        # Validate mutually exclusive parameters
        if entries is not None and category_account_id is not None:
            msg = (
                "Cannot specify both 'entries' and 'category_account_id'. "
                "Use 'entries' for full entry replacement or "
                "'category_account_id' for simple category swap."
            )
            raise ValidationError(msg)

        # Load transaction
        transaction = await self._load_transaction(transaction_id)

        # Unpost if needed (cross-cutting concern)
        was_posted = self._unpost_if_needed(transaction)

        # Route to operations based on inputs
        if entries is not None:
            await self._replace_entries(transaction, entries)
        elif category_account_id is not None:
            await self._change_category(transaction, category_account_id)

        if description is not None:
            self._update_description(transaction, description)

        if counterparty is not None:
            self._update_counterparty(transaction, counterparty)

        if metadata is not None:
            self._update_metadata(transaction, metadata)

        # Repost if requested and was originally posted (cross-cutting concern)
        if repost and was_posted:
            transaction.post()

        # Save changes (cross-cutting concern)
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

    async def _replace_entries(
        self,
        transaction: Transaction,
        entries: list[JournalEntryInput],
    ):
        # Load all referenced accounts
        account_ids = {entry.account_id for entry in entries}
        accounts = await self._load_accounts(account_ids)

        # Clear existing entries (preserves protected entries for bank imports)
        transaction.clear_entries()

        # Count protected entries that were preserved
        protected_count = len(transaction.protected_entries)

        # Validate minimum entries after considering protected ones
        min_entries = 2
        total_entries = protected_count + len(entries)
        if total_entries < min_entries:
            msg = (
                f"Transaction must have at least {min_entries} entries, "
                f"got {total_entries} (including {protected_count} protected)"
            )
            raise ValidationError(msg)

        # Add new entries
        for entry_input in entries:
            account = accounts[entry_input.account_id]
            money = Money(entry_input.amount, account.default_currency)

            if entry_input.is_debit:
                transaction.add_debit(account, money)
            else:
                transaction.add_credit(account, money)

    async def _change_category(
        self,
        transaction: Transaction,
        new_category_id: UUID,
    ):
        new_category = await self._account_repo.find_by_id(new_category_id)
        if not new_category:
            raise AccountNotFoundError(account_id=new_category_id)

        current_category_entry = None
        payment_entry = None

        for entry in transaction.entries:
            if entry.account.account_type in CATEGORY_ACCOUNT_TYPES:
                current_category_entry = entry
            elif entry.account.account_type in PAYMENT_ACCOUNT_TYPES:
                payment_entry = entry

        if not current_category_entry or not payment_entry:
            msg = (
                "Transaction does not have the expected structure "
                "(category + asset/liability). "
                "Use 'entries' parameter for multi-entry transactions."
            )
            raise BusinessRuleViolation(msg)

        # Get the amount from the current category entry
        amount = (
            current_category_entry.debit
            if current_category_entry.is_debit()
            else current_category_entry.credit
        )

        # Clear unprotected entries (preserves payment entry for bank imports)
        transaction.clear_entries()

        # Check if payment entry was preserved (bank import case)
        payment_preserved = any(
            e.account.account_type in PAYMENT_ACCOUNT_TYPES for e in transaction.entries
        )

        # Use domain service to build the new entries
        # InvalidAccountTypeError is raised by the service if new_category is invalid
        entry_specs = TransactionEntryService.build_category_swap_entries(
            new_category=new_category,
            payment_account=payment_entry.account,
            amount=amount,
            payment_preserved=payment_preserved,
        )

        # Apply the entry specifications to the transaction
        for spec in entry_specs:
            if spec.is_debit:
                transaction.add_debit(spec.account, spec.amount)
            else:
                transaction.add_credit(spec.account, spec.amount)

    def _update_description(
        self,
        transaction: Transaction,
        description: str,
    ):
        transaction.update_description(description)

    def _update_counterparty(
        self,
        transaction: Transaction,
        counterparty: str,
    ):
        transaction.update_counterparty(counterparty)

    def _update_metadata(
        self,
        transaction: Transaction,
        metadata: dict[str, Any],
    ):
        # Check for reserved keys
        reserved_in_update = set(metadata.keys()) & MetadataKeys.RESERVED_KEYS
        if reserved_in_update:
            reserved_list = ", ".join(sorted(reserved_in_update))
            msg = (
                f"Cannot modify reserved metadata keys via raw update: {reserved_list}."
                " Use transaction.update_metadata() for typed field updates."
            )
            raise ValidationError(msg)

        # Apply non-reserved metadata
        for key, value in metadata.items():
            transaction.set_metadata_raw(key, value)
