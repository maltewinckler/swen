"""Transaction aggregate root for the accounting domain."""

from datetime import datetime

from swen.domain.shared.time import utc_now
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from swen.domain.accounting.entities import Account, AccountType, JournalEntry
from swen.domain.accounting.exceptions import (
    EmptyDescriptionError,
    EmptyTransactionError,
    InvalidTransactionMetadataError,
    MixedCurrencyError,
    ProtectedEntryError,
    TransactionAlreadyPostedError,
    UnbalancedTransactionError,
    UnsupportedCurrencyError,
    ZeroAmountError,
)
from swen.domain.accounting.value_objects import (
    Currency,
    Money,
    TransactionMetadata,
    TransactionSource,
)
from swen.domain.shared.exceptions import BusinessRuleViolation, DomainException
from swen.domain.shared.iban import normalize_iban


class Transaction:
    """
    Ensures transaction consistency and implements double-entry rules.

    Enhanced with counterparty tracking for merchant/sender/recipient information
    and flexible metadata for categorization tags and additional context.

    Bank Import Fields (first-class properties):
    - source: Origin of the transaction (bank_import, manual, etc.)
    - source_iban: IBAN of the synced bank account
    - counterparty_iban: IBAN of the sender/recipient
    - is_internal_transfer: Whether this is a transfer between own accounts
    """

    def __init__(  # NOQA: PLR0913
        self,
        description: str,
        user_id: UUID,
        date: Optional[datetime] = None,
        counterparty: Optional[str] = None,
        counterparty_iban: Optional[str] = None,
        source: TransactionSource = TransactionSource.MANUAL,
        source_iban: Optional[str] = None,
        is_internal_transfer: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a new transaction.

        Parameters
        ----------
        description
            Human-readable transaction description
        user_id
            Owner user ID (required for multi-user support)
        date
            Transaction date (defaults to now)
        counterparty
            Name of merchant/sender/recipient (e.g., "REWE", "Employer GmbH")
        counterparty_iban
            IBAN of the sender/recipient (auto-normalized)
        source
            Origin of the transaction (defaults to MANUAL)
        source_iban
            IBAN of the source bank account for bank imports (auto-normalized)
        is_internal_transfer
            Whether this is a transfer between own accounts
        metadata
            Flexible key-value store for tags and categorization info
        """
        self._id = uuid4()
        self._user_id = user_id
        self._description = description
        self._date = date or utc_now()
        self._counterparty = counterparty
        self._counterparty_iban = normalize_iban(counterparty_iban)
        self._source = source
        self._source_iban = normalize_iban(source_iban)
        self._is_internal_transfer = is_internal_transfer
        # Ensure metadata always has source synced with first-class field
        self._metadata: Dict[str, Any] = metadata.copy() if metadata else {}
        self._metadata["source"] = source.value
        self._entries: List[JournalEntry] = []
        self._is_posted = False
        self._created_at = utc_now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def description(self) -> str:
        return self._description

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def is_posted(self) -> bool:
        return self._is_posted

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def counterparty(self) -> Optional[str]:
        return self._counterparty

    @property
    def counterparty_iban(self) -> Optional[str]:
        return self._counterparty_iban

    @property
    def source(self) -> TransactionSource:
        return self._source

    @property
    def source_iban(self) -> Optional[str]:
        return self._source_iban

    @property
    def metadata(self) -> TransactionMetadata:
        """Get metadata as validated Pydantic model.

        This is the standard way to access transaction metadata.
        Provides type-safe access with validation and normalized values.
        """
        return TransactionMetadata.model_validate(self._metadata)

    @property
    def metadata_raw(self) -> Dict[str, Any]:
        """Use this only when you need direct access to the underlying storage."""
        # TODO: Deprecate
        return self._metadata.copy()

    def set_metadata(self, metadata: TransactionMetadata) -> None:
        """Use this for setting complete metadata during transaction creation.

        Excludes None values to keep storage compact.
        Uses JSON mode to ensure datetime objects are serialized as ISO strings.

        Parameters
        ----------
        metadata
            Validated TransactionMetadata object

        Raises
        ------
        TransactionAlreadyPostedError
            If transaction is already posted
        """
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        # mode="json" ensures datetime objects are serialized as ISO strings
        self._metadata = metadata.model_dump(mode="json", exclude_none=True)

    @property
    def entries(self) -> List[JournalEntry]:
        return self._entries.copy()

    def add_entry(
        self,
        account: Account,
        debit: Optional[Money] = None,
        credit: Optional[Money] = None,
    ) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)

        # Disallow zero-amount entries; they are ambiguous and break debit/credit
        # detection based on sign/positivity.
        if debit is not None and debit.is_zero():
            msg = "debit"
            raise ZeroAmountError(msg)
        if credit is not None and credit.is_zero():
            msg = "credit"
            raise ZeroAmountError(msg)

        entry = JournalEntry(account, debit, credit)
        self._entries.append(entry)

    def add_debit(self, account: Account, amount: Money) -> None:
        self.add_entry(account, debit=amount)

    def add_credit(self, account: Account, amount: Money) -> None:
        self.add_entry(account, credit=amount)

    def set_metadata_raw(self, key: str, value: Any) -> None:
        # TODO: Deprecate
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        self._metadata[key] = value

    def update_metadata(self, **kwargs: Any) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)

        current = self.metadata
        updated = current.with_updates(**kwargs)
        self._metadata = updated.model_dump(mode="json", exclude_none=True)

    def get_metadata_raw(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)

    def has_metadata_raw(self, key: str) -> bool:
        return key in self._metadata

    def remove_metadata_raw(self, key: str) -> None:
        # TODO: Deprecate
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        self._metadata.pop(key, None)

    def update_counterparty(self, counterparty: Optional[str]) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        self._counterparty = counterparty

    def update_description(self, description: str) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        if not description or not description.strip():
            raise EmptyDescriptionError
        self._description = description.strip()

    def update_counterparty_iban(self, counterparty_iban: Optional[str]) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        self._counterparty_iban = normalize_iban(counterparty_iban)

    def mark_as_internal_transfer(self, is_transfer: bool = True) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)
        self._is_internal_transfer = is_transfer

    def remove_entry(self, entry_id: UUID) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)

        # Check protection before removal
        for entry in self._entries:
            if entry.id == entry_id and self.is_entry_protected(entry):
                raise ProtectedEntryError(entry_id=entry_id, reason="bank import")

        self._entries = [e for e in self._entries if e.id != entry_id]

    def clear_entries(self) -> None:
        if self.is_posted:
            raise TransactionAlreadyPostedError(self._id)

        if self.is_bank_import:
            # Preserve protected entries, only clear category entries
            self._entries = [e for e in self._entries if self.is_entry_protected(e)]
        else:
            self._entries.clear()

    def validate_double_entry(self) -> None:
        min_entries = 2
        if len(self._entries) < min_entries:
            raise EmptyTransactionError(len(self._entries))

        # Determine and enforce currency consistency.
        # MVP constraint: only EUR is supported, but we keep the implementation
        # ready for multi-currency by validating a single currency per transaction.
        currency: Currency | None = None
        for entry in self._entries:
            entry_money = entry.debit if entry.is_debit() else entry.credit
            if currency is None:
                currency = entry_money.currency
            elif entry_money.currency != currency:
                raise MixedCurrencyError(str(currency), str(entry_money.currency))

        currency = currency or Currency.default()
        if currency != Currency.default():
            # Keep a stable error message for MVP guardrails and tests.
            # This is intentionally explicit so callers understand multi-currency
            # is not supported yet.
            raise UnsupportedCurrencyError(str(currency), str(Currency.default()))

        # Calculate total debits and credits
        total_debits = Money(Decimal(0), currency)
        total_credits = Money(Decimal(0), currency)

        for entry in self._entries:
            if entry.is_debit():
                total_debits = total_debits + entry.debit
            else:
                total_credits = total_credits + entry.credit

        # Validate balance
        if total_debits != total_credits:
            raise UnbalancedTransactionError(str(total_debits), str(total_credits))

    def is_balanced(self) -> bool:
        try:
            self.validate_double_entry()
            return True
        except DomainException:
            return False

    def validate_business_rules(self) -> None:
        for entry in self._entries:
            if not entry.account.can_accept_transaction(entry.amount):
                amount = entry.amount
                name = entry.account.name
                msg = f"Account {name} cannot accept transaction of {amount}"
                raise BusinessRuleViolation(msg)

    def validate_metadata(self) -> None:
        # Empty metadata is allowed (legacy/test transactions)
        if not self._metadata:
            return

        try:
            # Attempt to parse - this validates all fields
            _ = self.metadata
        except Exception as e:
            raise InvalidTransactionMetadataError(str(e)) from e

    def post(self) -> None:
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)

        # Validate double-entry rules
        self.validate_double_entry()

        # Validate business rules
        self.validate_business_rules()

        # Validate metadata schema (catches corruption before permanence)
        self.validate_metadata()

        # Mark as posted (immutable)
        self._is_posted = True

    def unpost(self) -> None:
        # In a real system, this might require special permissions
        # and create an audit trail
        self._is_posted = False

    def total_amount(self) -> Money:
        if not self._entries:
            return Money(Decimal(0), Currency.default())

        first = self._entries[0]
        currency = (first.debit if first.is_debit() else first.credit).currency
        total = Money(Decimal(0), currency)
        for entry in self._entries:
            if entry.is_debit():
                total = total + entry.debit

        return total

    def get_entries_for_account(self, account: Account) -> List[JournalEntry]:
        return [e for e in self._entries if e.account == account]

    def involves_account(self, account: Account) -> bool:
        return any(e.account == account for e in self._entries)

    @property
    def is_internal_transfer(self) -> bool:
        """
        Check if this is an internal transfer between own accounts.

        An internal transfer is a transaction where money moves between
        two Asset accounts owned by the same user (e.g., checking → savings).
        These don't represent actual income or expenses.

        Detection uses a combined approach:
        1. Fast path: Check the stored field (set during creation/import)
        2. Legacy fallback: Check metadata (for old transactions)
        3. Final fallback: Check if all entries are Asset accounts
        """
        # Fast path: check the stored field first
        if self._is_internal_transfer:
            return True

        # Final fallback: check if all entries are Asset accounts
        # A transfer between own accounts has exactly 2 entries, both Asset type
        if len(self._entries) != 2:
            return False

        return all(
            entry.account.account_type == AccountType.ASSET for entry in self._entries
        )

    @property
    def is_bank_import(self) -> bool:
        """Check if this transaction originated from bank sync.

        Bank-imported transactions have protected asset entries that cannot
        be modified to preserve reconciliation with bank statements.
        """
        return self._source == TransactionSource.BANK_IMPORT

    @property
    def protected_entries(self) -> List[JournalEntry]:
        """Get entries that are protected from modification."""
        # Bank transactions are protected because fiddling with them would
        # break reconciliation with the bank statement.
        if not self.is_bank_import:
            return []
        return [e for e in self._entries if e.account.account_type == AccountType.ASSET]

    def is_entry_protected(self, entry: JournalEntry) -> bool:
        """Check if a specific entry is protected from modification."""
        if not self.is_bank_import:
            return False
        return entry.account.account_type == AccountType.ASSET

    def replace_unprotected_entries(
        self,
        new_entries: List[tuple[Account, Money, bool]],
    ) -> None:
        """Replace only unprotected (category) entries, preserving protected entries."""
        if self._is_posted:
            raise TransactionAlreadyPostedError(self._id)

        # Clear unprotected entries (preserves protected ones for bank imports)
        self.clear_entries()

        # Add new entries
        for account, amount, is_debit in new_entries:
            if is_debit:
                self.add_debit(account, amount)
            else:
                self.add_credit(account, amount)

    def convert_to_internal_transfer(
        self,
        new_asset_account: Account,
        transfer_hash: str,
    ) -> bool:
        """
        Convert this transaction from external Income/Expense to internal transfer.

        This transforms a transaction that was originally categorized as external
        (e.g., income from "Sonstige Einnahmen") into a proper internal transfer
        between Asset accounts.

        Parameters
        ----------
        new_asset_account
            The Asset account to replace Income/Expense with
        transfer_hash
            Canonical hash for transfer deduplication

        Returns
        -------
        True if conversion succeeded, False if no Income/Expense entry found
        """
        was_posted = self._is_posted
        if was_posted:
            self.unpost()

        try:
            # Find relevant entries
            income_expense_entry, asset_entry = self._find_convertible_entries()

            if income_expense_entry is None:
                return False

            # Rebuild as Asset↔Asset transfer
            self._rebuild_as_transfer(
                income_expense_entry=income_expense_entry,
                asset_entry=asset_entry,
                new_asset_account=new_asset_account,
            )

            # Update metadata and description
            source_account_name = asset_entry.account.name if asset_entry else None
            self._mark_as_internal_transfer(
                source_account_name=source_account_name,
                destination_account=new_asset_account,
                transfer_hash=transfer_hash,
            )
            self._update_transfer_description(new_asset_account, asset_entry)

            return True
        finally:
            # Re-post if it was posted before
            if was_posted:
                self.post()

    def _find_convertible_entries(
        self,
    ) -> tuple[Optional[JournalEntry], Optional[JournalEntry]]:
        income_expense_entry = None
        asset_entry = None

        for entry in self._entries:
            if entry.account.account_type in [AccountType.INCOME, AccountType.EXPENSE]:
                income_expense_entry = entry
            elif entry.account.account_type == AccountType.ASSET:
                asset_entry = entry

        return income_expense_entry, asset_entry

    def _rebuild_as_transfer(
        self,
        income_expense_entry: JournalEntry,
        asset_entry: Optional[JournalEntry],
        new_asset_account: Account,
    ) -> None:
        """
        Clear entries and rebuild as Asset<->Asset transfer.

        Converts:
        - Debit Expense -> Debit new Asset (money going to destination)
        - Credit Income -> Credit new Asset (money coming from source)

        Note: For bank imports, clear_entries() preserves the asset entry.
        We check if it was preserved to avoid adding a duplicate.
        """
        self.clear_entries()

        # For bank imports, clear_entries() preserves the asset entry.
        # Check if asset was preserved to avoid adding a duplicate.
        asset_preserved = any(
            e.account.account_type == AccountType.ASSET for e in self._entries
        )

        if income_expense_entry.is_debit():
            # Old: Debit Expense → New: Debit Asset (destination)
            self.add_debit(new_asset_account, income_expense_entry.debit)
            if asset_entry and not asset_preserved:
                self.add_credit(asset_entry.account, income_expense_entry.debit)
        else:
            # Old: Credit Income → New: Credit Asset (source)
            if asset_entry and not asset_preserved:
                self.add_debit(asset_entry.account, income_expense_entry.credit)
            self.add_credit(new_asset_account, income_expense_entry.credit)

    def _mark_as_internal_transfer(
        self,
        source_account_name: Optional[str],
        destination_account: Account,
        transfer_hash: str,
    ) -> None:
        # Set first-class fields
        self._is_internal_transfer = True
        self._counterparty = destination_account.name

        # Update metadata with transfer context (for reconciliation tracking)
        self.update_metadata(
            source_account=source_account_name,
            destination_account=destination_account.name,
            transfer_identity_hash=transfer_hash,
        )

    def _update_transfer_description(
        self,
        new_asset_account: Account,
        original_asset_entry: Optional[JournalEntry],
    ) -> None:
        direction = self._determine_transfer_direction(original_asset_entry)
        self._description = f"Transfer {direction} {new_asset_account.name}"
        self._counterparty = new_asset_account.name

    def _determine_transfer_direction(
        self,
        original_asset_entry: Optional[JournalEntry],
    ) -> str:
        if original_asset_entry is None:
            return "from"

        # If original asset is now credited, money went out
        for entry in self._entries:
            if (
                entry.account == original_asset_entry.account
                and entry.credit.amount > 0
            ):
                return "to"

        return "from"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Transaction):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        status = "POSTED" if self._is_posted else "DRAFT"
        parts = [f"Transaction[{status}]: {self._description}"]

        if self._counterparty:
            parts.append(f"counterparty={self._counterparty}")

        parts.append(f"({len(self._entries)} entries)")

        if self._metadata:
            tags = ", ".join(f"{k}={v}" for k, v in self._metadata.items())
            parts.append(f"[{tags}]")

        return " ".join(parts)
