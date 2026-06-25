"""Domain service for editing existing transactions.

This domain service encapsulates the business rules for editing transactions,
including:
- Replacing entries (with protected-entry preservation for bank imports)
- Recategorizing transactions (validating structure, swapping category)
- Metadata updates (enforcing reserved key constraints)

It operates purely on the Transaction aggregate and Account entities,
delegating entry building to TransactionEntryService where appropriate.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.services.transaction_entry_service import (
    CATEGORY_ACCOUNT_TYPES,
    PAYMENT_ACCOUNT_TYPES,
    TransactionEntryService,
)
from swen.domain.accounting.value_objects import (
    JournalEntryInput,
    MetadataKeys,
    Money,
)
from swen.domain.shared.exceptions import BusinessRuleViolation, ValidationError


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
        """Recategorize a transaction.

        Business rules:
        - Transaction must have exactly one category + one payment entry
        - New category must match transaction direction (expense/income)
        - Bank imports preserve the payment entry
        """
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
        entry_specs = TransactionEntryService.build_category_swap_entries(
            new_category=counter_account,
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
