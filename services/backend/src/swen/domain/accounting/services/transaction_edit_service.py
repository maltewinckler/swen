"""Domain service for editing existing transactions.

This domain service encapsulates the business rules for editing transactions,
including:
- Replacing entries (with protected-entry preservation for bank imports)
- Recategorizing transactions (validating structure, swapping category)
- Metadata updates (enforcing reserved key constraints)

It operates purely on the Transaction aggregate and Account entities.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import (
    CATEGORY_ACCOUNT_TYPES,
    Account,
    JournalEntry,
)
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.value_objects import (
    JournalEntryInput,
    MetadataKeys,
    Money,
)
from swen.domain.shared.exceptions import BusinessRuleViolation, ValidationError


def _extract_counter_account_entry(transaction: Transaction) -> JournalEntry:
    # Find the existing category entry (Income or Expense)
    category_entry_to_replace = None
    for entry in transaction.entries:
        if entry.account.account_type in CATEGORY_ACCOUNT_TYPES:
            # In multi entry trx, we cannot support this way of changing yet.
            if category_entry_to_replace is not None:
                msg = (
                    "Transaction has multiple category entries; "
                    "use 'replace_entries' for multi-entry transactions."
                )
                raise BusinessRuleViolation(msg)
            category_entry_to_replace = entry

    if category_entry_to_replace is None:
        msg = "Transaction has no category (Income/Expense) entry to replace."
        raise BusinessRuleViolation(msg)
    return category_entry_to_replace


class TransactionEditService:
    """Domain service for editing existing transactions.

    This service encapsulates the business rules for transaction editing.
    It is stateless and operates purely on the provided domain objects.
    """

    @staticmethod
    def replace_entries(
        transaction: Transaction,
        entries: list[JournalEntryInput],
        accounts: dict[UUID, Account],
    ) -> None:
        """Replace transaction entries with new ones.

        Business rules:
        - Bank imports preserve protected (asset) entries
        - Minimum 2 entries required after considering protected ones
        """
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

    @staticmethod
    def change_counter_account(
        transaction: Transaction,
        counter_account: Account,
    ) -> None:
        """Recategorize a transaction by replacing the category entry.

        Business rules:
        - Transaction must have exactly one category (Income/Expense) entry
        - New category must match the transaction direction (expense/income)
        - The payment entry is preserved — only the category entry is replaced

        This is a targeted 2-step operation:
        1. Remove the existing category entry
        2. Add the new category entry with the same amount and debit/credit direction
        """
        # Validate new category is Income or Expense
        if counter_account.account_type not in CATEGORY_ACCOUNT_TYPES:
            raise InvalidAccountTypeError(
                counter_account.account_type.value,
                ["expense", "income"],
            )

        # Find the existing category entry (Income or Expense)
        counter_entry_to_replace = _extract_counter_account_entry(transaction)

        # Record the amount and debit/credit direction from the old entry
        # Use is_debit() to determine which field holds the actual amount
        if counter_entry_to_replace.is_debit():
            amount = counter_entry_to_replace.debit
            is_debit = True
        else:
            amount = counter_entry_to_replace.credit
            is_debit = False

        # Remove the old category entry
        transaction.remove_entry(counter_entry_to_replace.id)

        # Add the new category entry with the same direction and amount
        if is_debit:
            transaction.add_debit(counter_account, amount)
        else:
            transaction.add_credit(counter_account, amount)

    @staticmethod
    def update_metadata(
        transaction: Transaction,
        metadata: dict[str, Any],
    ) -> None:
        """Update metadata with reserved-key enforcement.

        Business rules:
        - Reserved keys cannot be modified via raw update
        """
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
