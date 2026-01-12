"""Unit tests for Transaction aggregate entry protection.

Tests the domain invariant that bank-imported transactions have protected
asset entries that cannot be modified.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import ProtectedEntryError
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def checking_account():
    """Create a checking (asset) account."""
    return Account(
        name="Checking",
        account_type=AccountType.ASSET,
        account_number="1000",
        user_id=uuid4(),
    )


@pytest.fixture
def groceries_account():
    """Create a groceries (expense) account."""
    return Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="6000",
        user_id=uuid4(),
    )


@pytest.fixture
def restaurant_account():
    """Create a restaurant (expense) account."""
    return Account(
        name="Restaurant",
        account_type=AccountType.EXPENSE,
        account_number="6001",
        user_id=uuid4(),
    )


@pytest.fixture
def salary_account():
    """Create a salary (income) account."""
    return Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="4000",
        user_id=uuid4(),
    )


@pytest.fixture
def amount():
    """Create a test amount."""
    return Money(Decimal("50.00"), Currency("EUR"))


@pytest.fixture
def manual_transaction(user_id, checking_account, groceries_account, amount):
    """Create a manual transaction (not from bank import)."""
    txn = Transaction(
        description="Grocery shopping",
        user_id=user_id,
        source=TransactionSource.MANUAL,  # Use first-class field
    )
    txn.add_debit(groceries_account, amount)
    txn.add_credit(checking_account, amount)
    return txn


@pytest.fixture
def bank_import_transaction(user_id, checking_account, groceries_account, amount):
    """Create a bank-imported transaction."""
    txn = Transaction(
        description="REWE SAGT DANKE",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,  # Use first-class field
    )
    txn.add_debit(groceries_account, amount)
    txn.add_credit(checking_account, amount)
    return txn


class TestIsBankImport:
    """Tests for is_bank_import property."""

    def test_bank_import_returns_true(self, bank_import_transaction):
        """Bank-imported transaction returns True."""
        assert bank_import_transaction.is_bank_import is True

    def test_manual_returns_false(self, manual_transaction):
        """Manual transaction returns False."""
        assert manual_transaction.is_bank_import is False

    def test_no_source_returns_false(self, user_id, checking_account, groceries_account, amount):
        """Transaction without source metadata returns False."""
        txn = Transaction(description="Test", user_id=user_id)
        txn.add_debit(groceries_account, amount)
        txn.add_credit(checking_account, amount)
        assert txn.is_bank_import is False


class TestProtectedEntries:
    """Tests for protected_entries property."""

    def test_bank_import_protects_asset_entries(self, bank_import_transaction, checking_account):
        """Bank import protects asset (bank account) entries."""
        protected = bank_import_transaction.protected_entries
        assert len(protected) == 1
        assert protected[0].account.account_type == AccountType.ASSET

    def test_bank_import_does_not_protect_expense_entries(
        self, bank_import_transaction, groceries_account
    ):
        """Bank import does not protect expense entries."""
        protected = bank_import_transaction.protected_entries
        assert all(e.account.account_type != AccountType.EXPENSE for e in protected)

    def test_manual_transaction_has_no_protected_entries(self, manual_transaction):
        """Manual transactions have no protected entries."""
        assert len(manual_transaction.protected_entries) == 0


class TestIsEntryProtected:
    """Tests for is_entry_protected method."""

    def test_asset_entry_protected_in_bank_import(self, bank_import_transaction):
        """Asset entry is protected in bank-imported transaction."""
        asset_entry = next(
            e for e in bank_import_transaction.entries
            if e.account.account_type == AccountType.ASSET
        )
        assert bank_import_transaction.is_entry_protected(asset_entry) is True

    def test_expense_entry_not_protected_in_bank_import(self, bank_import_transaction):
        """Expense entry is not protected in bank-imported transaction."""
        expense_entry = next(
            e for e in bank_import_transaction.entries
            if e.account.account_type == AccountType.EXPENSE
        )
        assert bank_import_transaction.is_entry_protected(expense_entry) is False

    def test_no_entries_protected_in_manual(self, manual_transaction):
        """No entries are protected in manual transaction."""
        for entry in manual_transaction.entries:
            assert manual_transaction.is_entry_protected(entry) is False


class TestRemoveEntry:
    """Tests for remove_entry with protection enforcement."""

    def test_remove_protected_entry_raises_error(self, bank_import_transaction):
        """Removing protected entry raises ProtectedEntryError."""
        asset_entry = next(
            e for e in bank_import_transaction.entries
            if e.account.account_type == AccountType.ASSET
        )

        with pytest.raises(ProtectedEntryError) as exc_info:
            bank_import_transaction.remove_entry(asset_entry.id)

        assert "protected" in str(exc_info.value).lower()
        assert "bank import" in str(exc_info.value).lower()

    def test_remove_unprotected_entry_succeeds(self, bank_import_transaction):
        """Removing unprotected (category) entry succeeds."""
        expense_entry = next(
            e for e in bank_import_transaction.entries
            if e.account.account_type == AccountType.EXPENSE
        )
        initial_count = len(bank_import_transaction.entries)

        bank_import_transaction.remove_entry(expense_entry.id)

        assert len(bank_import_transaction.entries) == initial_count - 1

    def test_remove_any_entry_from_manual_succeeds(self, manual_transaction):
        """Any entry can be removed from manual transaction."""
        asset_entry = next(
            e for e in manual_transaction.entries
            if e.account.account_type == AccountType.ASSET
        )

        manual_transaction.remove_entry(asset_entry.id)

        assert len(manual_transaction.entries) == 1


class TestClearEntries:
    """Tests for clear_entries with protection preservation."""

    def test_clear_preserves_protected_entries_in_bank_import(self, bank_import_transaction):
        """Clear entries preserves protected (asset) entries for bank imports."""
        bank_import_transaction.clear_entries()

        # Only asset entry should remain
        assert len(bank_import_transaction.entries) == 1
        assert bank_import_transaction.entries[0].account.account_type == AccountType.ASSET

    def test_clear_removes_all_entries_in_manual(self, manual_transaction):
        """Clear entries removes all entries for manual transactions."""
        manual_transaction.clear_entries()

        assert len(manual_transaction.entries) == 0


class TestReplaceUnprotectedEntries:
    """Tests for replace_unprotected_entries method."""

    def test_replace_preserves_protected_in_bank_import(
        self, bank_import_transaction, restaurant_account, amount
    ):
        """Replace preserves protected asset entry for bank imports."""
        # Replace groceries with restaurant
        bank_import_transaction.replace_unprotected_entries([
            (restaurant_account, amount, True),  # debit restaurant
        ])

        entries = bank_import_transaction.entries
        assert len(entries) == 2

        # Asset entry should still exist
        assert any(e.account.account_type == AccountType.ASSET for e in entries)
        # New expense should exist
        assert any(e.account.name == "Restaurant" for e in entries)

    def test_replace_splits_category_in_bank_import(
        self, bank_import_transaction, groceries_account, restaurant_account
    ):
        """Can split into multiple categories for bank imports."""
        amount1 = Money(Decimal("30.00"), Currency("EUR"))
        amount2 = Money(Decimal("20.00"), Currency("EUR"))

        bank_import_transaction.replace_unprotected_entries([
            (groceries_account, amount1, True),  # debit 30
            (restaurant_account, amount2, True),  # debit 20
        ])

        entries = bank_import_transaction.entries
        assert len(entries) == 3  # 1 protected asset + 2 new expenses

    def test_replace_all_in_manual(
        self, manual_transaction, checking_account, restaurant_account, amount
    ):
        """All entries are replaced for manual transactions."""
        manual_transaction.replace_unprotected_entries([
            (restaurant_account, amount, True),  # debit
            (checking_account, amount, False),   # credit
        ])

        entries = manual_transaction.entries
        assert len(entries) == 2
        assert any(e.account.name == "Restaurant" for e in entries)


class TestBankImportIncomeTransaction:
    """Tests for bank-imported income transactions."""

    @pytest.fixture
    def bank_income_transaction(self, user_id, checking_account, salary_account, amount):
        """Create a bank-imported income transaction."""
        txn = Transaction(
            description="SALARY PAYMENT",
            user_id=user_id,
            source=TransactionSource.BANK_IMPORT,  # Use first-class field
        )
        txn.add_debit(checking_account, amount)  # Asset increases
        txn.add_credit(salary_account, amount)   # Income
        return txn

    def test_asset_protected_in_income_transaction(self, bank_income_transaction):
        """Asset entry is protected in income transaction too."""
        protected = bank_income_transaction.protected_entries
        assert len(protected) == 1
        assert protected[0].account.account_type == AccountType.ASSET

    def test_income_entry_not_protected(self, bank_income_transaction):
        """Income entry is not protected."""
        income_entry = next(
            e for e in bank_income_transaction.entries
            if e.account.account_type == AccountType.INCOME
        )
        assert bank_income_transaction.is_entry_protected(income_entry) is False


class TestPostedTransactionProtection:
    """Tests for interaction between posting and protection."""

    def test_unpost_allows_category_change(
        self, bank_import_transaction, restaurant_account, amount
    ):
        """Unposting allows changing category entries."""
        bank_import_transaction.post()
        bank_import_transaction.unpost()

        # Should be able to clear category entries
        bank_import_transaction.clear_entries()
        bank_import_transaction.add_debit(restaurant_account, amount)

        assert len(bank_import_transaction.entries) == 2  # asset + new category

    def test_unpost_still_protects_asset(self, bank_import_transaction):
        """Unposting still protects asset entry from removal."""
        bank_import_transaction.post()
        bank_import_transaction.unpost()

        asset_entry = next(
            e for e in bank_import_transaction.entries
            if e.account.account_type == AccountType.ASSET
        )

        with pytest.raises(ProtectedEntryError):
            bank_import_transaction.remove_entry(asset_entry.id)
