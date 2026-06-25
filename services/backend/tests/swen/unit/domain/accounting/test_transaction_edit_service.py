"""Unit tests for TransactionEditService domain service."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.services import TransactionEditService
from swen.domain.accounting.value_objects import Currency, JournalEntryInput, Money
from swen.domain.shared.exceptions import BusinessRuleViolation, ValidationError


@pytest.fixture
def mock_account():
    """Create a mock account."""

    def _create(
        account_type: AccountType = AccountType.ASSET,
        name: str | None = None,
        currency: Currency = Currency("EUR"),
    ):
        account = MagicMock()
        account.id = uuid4()
        account.name = name or f"Test {account_type.value}"
        account.account_type = account_type
        account.default_currency = currency
        account.is_active = True
        return account

    return _create


@pytest.fixture
def mock_transaction():
    """Create a mock transaction."""

    def _create(
        is_bank_import: bool = False,
        is_posted: bool = False,
        entries: list | None = None,
        protected_count: int = 0,
    ):
        txn = MagicMock()
        txn.is_posted = is_posted
        txn.is_bank_import = is_bank_import
        txn.entries = entries or []
        txn.protected_entries = [MagicMock() for _ in range(protected_count)]

        # Track calls
        txn.added_debits = []
        txn.added_credits = []
        txn.removed_entry_ids = []

        def mock_add_debit(account, money):
            txn.added_debits.append((account, money))

        def mock_add_credit(account, money):
            txn.added_credits.append((account, money))

        def mock_remove_entry(entry_id):
            txn.removed_entry_ids.append(entry_id)

        txn.add_debit = MagicMock(side_effect=mock_add_debit)
        txn.add_credit = MagicMock(side_effect=mock_add_credit)
        txn.remove_entry = MagicMock(side_effect=mock_remove_entry)
        txn.clear_entries = MagicMock()
        txn.update_description = MagicMock()
        txn.update_counterparty = MagicMock()
        txn.set_metadata_raw = MagicMock()

        return txn

    return _create


class TestTransactionEditServiceReplaceEntries:
    """Tests for TransactionEditService.replace_entries."""

    def test_replace_entries_basic(
        self,
        mock_transaction,
        mock_account,
    ):
        """Basic entry replacement works."""
        expense = mock_account(AccountType.EXPENSE, "Groceries")
        asset = mock_account(AccountType.ASSET, "Checking")

        accounts = {expense.id: expense, asset.id: asset}
        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("50.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("50.00")),
        ]

        txn = mock_transaction()
        TransactionEditService.replace_entries(txn, entries, accounts)

        txn.clear_entries.assert_called_once()
        assert txn.add_debit.call_count == 1
        assert txn.add_credit.call_count == 1

    def test_replace_entries_requires_minimum_two(
        self,
        mock_transaction,
        mock_account,
    ):
        """At least 2 entries required."""
        expense = mock_account(AccountType.EXPENSE, "Groceries")
        asset = mock_account(AccountType.ASSET, "Checking")

        accounts = {expense.id: expense, asset.id: asset}
        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("50.00")),
        ]

        txn = mock_transaction()
        with pytest.raises(ValidationError, match="at least 2"):
            TransactionEditService.replace_entries(txn, entries, accounts)

        txn.clear_entries.assert_called_once()

    def test_replace_entries_with_protected_entries_passes_minimum(
        self,
        mock_transaction,
        mock_account,
    ):
        """With 1 protected entry, only 1 new entry required."""
        expense = mock_account(AccountType.EXPENSE, "Groceries")

        accounts = {expense.id: expense}
        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("50.00")),
        ]

        txn = mock_transaction(protected_count=1)
        TransactionEditService.replace_entries(txn, entries, accounts)

        # 1 protected + 1 new = 2, passes minimum
        assert txn.add_debit.call_count == 1

    def test_replace_entries_with_protected_entries_fails_minimum(
        self,
        mock_transaction,
        mock_account,
    ):
        """With 1 protected entry, 0 new entries fails minimum."""
        accounts = {}
        entries = []

        txn = mock_transaction(protected_count=1)
        with pytest.raises(ValidationError, match="at least 2"):
            TransactionEditService.replace_entries(txn, entries, accounts)

    def test_replace_entries_account_not_found(
        self,
        mock_transaction,
        mock_account,
    ):
        """Raises KeyError for unknown account (dict lookup)."""
        expense = mock_account(AccountType.EXPENSE, "Groceries")
        asset = mock_account(AccountType.ASSET, "Checking")

        accounts = {expense.id: expense}
        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("50.00")),
            JournalEntryInput.credit_entry(uuid4(), Decimal("50.00")),
        ]

        txn = mock_transaction()
        with pytest.raises(KeyError):
            TransactionEditService.replace_entries(txn, entries, accounts)

    def test_replace_entries_multi_entry(
        self,
        mock_transaction,
        mock_account,
    ):
        """Multi-entry replacement works."""
        expense1 = mock_account(AccountType.EXPENSE, "Groceries")
        expense2 = mock_account(AccountType.EXPENSE, "Restaurant")
        asset = mock_account(AccountType.ASSET, "Checking")

        accounts = {expense1.id: expense1, expense2.id: expense2, asset.id: asset}
        entries = [
            JournalEntryInput.debit_entry(expense1.id, Decimal("30.00")),
            JournalEntryInput.debit_entry(expense2.id, Decimal("20.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("50.00")),
        ]

        txn = mock_transaction()
        TransactionEditService.replace_entries(txn, entries, accounts)

        assert txn.add_debit.call_count == 2
        assert txn.add_credit.call_count == 1


class TestTransactionEditServiceChangeCounterAccount:
    """Tests for TransactionEditService.change_counter_account."""

    def test_change_counter_account_basic(
        self,
        mock_transaction,
        mock_account,
    ):
        """Basic category change replaces only the category entry."""
        old_expense = mock_account(AccountType.EXPENSE, "Groceries")
        new_expense = mock_account(AccountType.EXPENSE, "Restaurant")
        asset = mock_account(AccountType.ASSET, "Checking")

        # Create mock entries
        category_entry = MagicMock()
        category_entry.account = old_expense
        category_entry.id = uuid4()
        category_entry.is_debit.return_value = True
        category_entry.debit = Money(Decimal("50.00"), Currency("EUR"))
        category_entry.credit = Money(Decimal("0"), Currency("EUR"))

        payment_entry = MagicMock()
        payment_entry.account = asset
        payment_entry.is_debit.return_value = False

        txn = mock_transaction(entries=[category_entry, payment_entry])

        TransactionEditService.change_counter_account(txn, new_expense)

        # Should NOT call clear_entries
        txn.clear_entries.assert_not_called()

        # Should remove the old category entry
        txn.remove_entry.assert_called_once_with(category_entry.id)

        # Should add the new category entry as debit (same direction)
        txn.add_debit.assert_called_once_with(new_expense, category_entry.debit)

        # Payment entry should be untouched
        assert len(txn.added_credits) == 0

    def test_change_counter_account_with_liability(
        self,
        mock_transaction,
        mock_account,
    ):
        """Category change works with liability (credit card) as payment account."""
        old_expense = mock_account(AccountType.EXPENSE, "Groceries")
        new_expense = mock_account(AccountType.EXPENSE, "Restaurant")
        liability = mock_account(AccountType.LIABILITY, "Credit Card")

        category_entry = MagicMock()
        category_entry.account = old_expense
        category_entry.id = uuid4()
        category_entry.is_debit.return_value = True
        category_entry.debit = Money(Decimal("50.00"), Currency("EUR"))
        category_entry.credit = Money(Decimal("0"), Currency("EUR"))

        payment_entry = MagicMock()
        payment_entry.account = liability
        payment_entry.is_debit.return_value = False

        txn = mock_transaction(entries=[category_entry, payment_entry])

        TransactionEditService.change_counter_account(txn, new_expense)

        txn.clear_entries.assert_not_called()
        txn.remove_entry.assert_called_once_with(category_entry.id)
        txn.add_debit.assert_called_once()

    def test_change_counter_account_income(
        self,
        mock_transaction,
        mock_account,
    ):
        """Category change works for income transactions (credit direction)."""
        old_income = mock_account(AccountType.INCOME, "Salary")
        new_income = mock_account(AccountType.INCOME, "Freelance")
        asset = mock_account(AccountType.ASSET, "Checking")

        category_entry = MagicMock()
        category_entry.account = old_income
        category_entry.id = uuid4()
        category_entry.is_debit.return_value = False
        category_entry.debit = Money(Decimal("0"), Currency("EUR"))
        category_entry.credit = Money(Decimal("1000.00"), Currency("EUR"))

        payment_entry = MagicMock()
        payment_entry.account = asset
        payment_entry.is_debit.return_value = True

        txn = mock_transaction(entries=[payment_entry, category_entry])

        TransactionEditService.change_counter_account(txn, new_income)

        txn.clear_entries.assert_not_called()
        txn.remove_entry.assert_called_once_with(category_entry.id)

        # Should add as credit (same direction as old income entry)
        txn.add_credit.assert_called_once_with(new_income, category_entry.credit)

    def test_change_counter_account_missing_category_entry(
        self,
        mock_transaction,
        mock_account,
    ):
        """Raises BusinessRuleViolation when no category entry found."""
        asset = mock_account(AccountType.ASSET, "Checking")

        # Only payment entries, no category
        payment_entry = MagicMock()
        payment_entry.account = asset
        payment_entry.is_debit.return_value = False

        txn = mock_transaction(entries=[payment_entry])

        # Use INCOME type so it passes the account_type validation
        # but there's no INCOME entry in the transaction
        income = mock_account(AccountType.INCOME, "Salary")
        with pytest.raises(BusinessRuleViolation, match="category"):
            TransactionEditService.change_counter_account(txn, income)

    def test_change_counter_account_invalid_new_category_type(
        self,
        mock_transaction,
        mock_account,
    ):
        """Raises InvalidAccountTypeError when new category is not expense/income."""
        old_expense = mock_account(AccountType.EXPENSE, "Groceries")
        asset = mock_account(AccountType.ASSET, "Checking")

        category_entry = MagicMock()
        category_entry.account = old_expense
        category_entry.is_debit.return_value = True
        category_entry.debit = Money(Decimal("50.00"), Currency("EUR"))
        category_entry.credit = Money(Decimal("0"), Currency("EUR"))

        payment_entry = MagicMock()
        payment_entry.account = asset

        txn = mock_transaction(entries=[category_entry, payment_entry])

        # Asset account is not a valid category
        invalid_category = mock_account(AccountType.ASSET, "Savings")
        with pytest.raises(Exception, match="asset"):
            TransactionEditService.change_counter_account(txn, invalid_category)

    def test_change_counter_account_multiple_category_entries_raises(
        self,
        mock_transaction,
        mock_account,
    ):
        """Raises BusinessRuleViolation when transaction has multiple category entries."""
        expense = mock_account(AccountType.EXPENSE, "Groceries")
        income = mock_account(AccountType.INCOME, "Salary")
        asset = mock_account(AccountType.ASSET, "Checking")

        category_entry1 = MagicMock()
        category_entry1.account = expense
        category_entry1.id = uuid4()
        category_entry1.is_debit.return_value = True
        category_entry1.debit = Money(Decimal("50.00"), Currency("EUR"))
        category_entry1.credit = Money(Decimal("0"), Currency("EUR"))

        category_entry2 = MagicMock()
        category_entry2.account = income
        category_entry2.id = uuid4()
        category_entry2.is_debit.return_value = False
        category_entry2.debit = Money(Decimal("0"), Currency("EUR"))
        category_entry2.credit = Money(Decimal("100.00"), Currency("EUR"))

        payment_entry = MagicMock()
        payment_entry.account = asset

        txn = mock_transaction(
            entries=[category_entry1, category_entry2, payment_entry]
        )

        new_expense = mock_account(AccountType.EXPENSE, "Restaurant")
        with pytest.raises(BusinessRuleViolation, match="multiple category entries"):
            TransactionEditService.change_counter_account(txn, new_expense)


class TestTransactionEditServiceUpdateMetadata:
    """Tests for TransactionEditService.update_metadata."""

    def test_update_metadata_basic(
        self,
        mock_transaction,
    ):
        """Basic metadata update works."""
        txn = mock_transaction()
        TransactionEditService.update_metadata(txn, {"custom_key": "value123"})

        txn.set_metadata_raw.assert_called_once_with("custom_key", "value123")

    def test_update_metadata_rejects_reserved_keys(
        self,
        mock_transaction,
    ):
        """Reserved metadata keys are rejected."""
        txn = mock_transaction()
        with pytest.raises(ValidationError, match="reserved"):
            TransactionEditService.update_metadata(txn, {"source": "hacked"})

        txn.set_metadata_raw.assert_not_called()

    def test_update_metadata_allows_non_reserved_keys(
        self,
        mock_transaction,
    ):
        """Non-reserved keys are allowed."""
        txn = mock_transaction()
        TransactionEditService.update_metadata(
            txn,
            {
                "custom_tag": "value",
                "merchant": "TEST",
                "is_recurring": False,
            },
        )

        assert txn.set_metadata_raw.call_count == 3
