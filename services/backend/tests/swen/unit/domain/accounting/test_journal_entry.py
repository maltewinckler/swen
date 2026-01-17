"""Tests for the JournalEntry entity."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType, JournalEntry
from swen.domain.accounting.value_objects import Money

# Test user ID for all journal entry tests
TEST_USER_ID = uuid4()


class TestJournalEntry:
    """Test cases for JournalEntry entity."""

    def test_debit_entry_creation(self):
        """Test creating a debit journal entry."""
        account = Account("Checking", AccountType.ASSET, "1000", TEST_USER_ID)
        amount = Money(amount=Decimal("100.00"))
        entry = JournalEntry(account, debit=amount)

        assert entry.account == account
        assert entry.debit == amount
        assert entry.credit == Money(amount=Decimal(0))
        assert entry.amount == amount
        assert entry.is_debit() is True
        assert entry.is_credit() is False
        assert isinstance(entry.id, UUID)

    def test_credit_entry_creation(self):
        """Test creating a credit journal entry."""
        account = Account("Salary Income", AccountType.INCOME, "4000", TEST_USER_ID)
        amount = Money(amount=Decimal("2000.00"))
        entry = JournalEntry(account, credit=amount)

        assert entry.account == account
        assert entry.credit == amount
        assert entry.debit == Money(amount=Decimal(0))
        assert entry.amount == amount
        assert entry.is_credit() is True
        assert entry.is_debit() is False

    def test_entry_validation_both_debit_and_credit(self):
        """Test that entry cannot have both debit and credit."""
        account = Account("Test", AccountType.ASSET, "1001", TEST_USER_ID)
        amount = Money(amount=Decimal("100.00"))

        with pytest.raises(ValueError, match="exactly one of debit or credit"):
            JournalEntry(account, debit=amount, credit=amount)

    def test_entry_validation_neither_debit_nor_credit(self):
        """Test that entry must have either debit or credit."""
        account = Account("Test", AccountType.ASSET, "1002", TEST_USER_ID)

        with pytest.raises(ValueError, match="exactly one of debit or credit"):
            JournalEntry(account)

    def test_entry_validation_negative_debit(self):
        """Test that debit amounts must be positive."""
        account = Account("Test", AccountType.ASSET, "1003", TEST_USER_ID)
        negative_amount = Money(amount=Decimal("-100.00"))

        with pytest.raises(ValueError, match="Debit amount must be positive"):
            JournalEntry(account, debit=negative_amount)

    def test_entry_validation_negative_credit(self):
        """Test that credit amounts must be positive."""
        account = Account("Test", AccountType.INCOME, "4001", TEST_USER_ID)
        negative_amount = Money(amount=Decimal("-100.00"))

        with pytest.raises(ValueError, match="Credit amount must be positive"):
            JournalEntry(account, credit=negative_amount)

    def test_entry_with_zero_amounts(self):
        """Test that zero amounts are handled correctly."""
        account = Account("Test", AccountType.ASSET, "1004", TEST_USER_ID)
        zero_amount = Money(amount=Decimal(0))

        # Zero debit should be valid
        debit_entry = JournalEntry(account, debit=zero_amount)
        assert debit_entry.is_debit() is False  # Zero is not positive
        assert debit_entry.is_credit() is False

        # Zero credit should be valid
        credit_entry = JournalEntry(account, credit=zero_amount)
        assert credit_entry.is_credit() is False  # Zero is not positive
        assert credit_entry.is_debit() is False

    def test_entry_amount_property(self):
        """Test the amount property returns the absolute value."""
        account = Account("Test", AccountType.ASSET, "1005", TEST_USER_ID)
        amount = Money(amount=Decimal("150.00"))

        debit_entry = JournalEntry(account, debit=amount)
        assert debit_entry.amount == amount

        credit_entry = JournalEntry(account, credit=amount)
        assert credit_entry.amount == amount

    def test_entry_with_different_currencies(self):
        """Test entries with different currencies."""
        account = Account("Test", AccountType.ASSET, "1006", TEST_USER_ID)
        usd_amount = Money(amount=Decimal("100.00"), currency="USD")
        eur_amount = Money(amount=Decimal("85.00"), currency="EUR")

        usd_entry = JournalEntry(account, debit=usd_amount)
        eur_entry = JournalEntry(account, credit=eur_amount)

        assert usd_entry.amount.currency == "USD"
        assert eur_entry.amount.currency == "EUR"

    def test_entry_equality(self):
        """Test journal entry equality and hashing."""
        account = Account("Test", AccountType.ASSET, "1007", TEST_USER_ID)
        amount = Money(amount=Decimal("100.00"))

        entry1 = JournalEntry(account, debit=amount)
        entry2 = JournalEntry(account, debit=amount)
        entry3 = entry1

        # Different entries should not be equal even with same properties
        assert entry1 != entry2
        assert entry1 == entry3

        # Should be hashable for use in sets/dicts
        entry_set = {entry1, entry2, entry3}
        assert len(entry_set) == 2  # entry1 and entry3 are same object

    def test_entry_string_representation(self):
        """Test string representation of journal entries."""
        account = Account("Checking Account", AccountType.ASSET, "1008", TEST_USER_ID)
        amount = Money(amount=Decimal("100.00"))

        debit_entry = JournalEntry(account, debit=amount)
        credit_entry = JournalEntry(account, credit=amount)

        debit_str = str(debit_entry)
        credit_str = str(credit_entry)

        assert "Debit" in debit_str
        assert "Checking Account" in debit_str
        assert "100.00" in debit_str

        assert "Credit" in credit_str
        assert "Checking Account" in credit_str
        assert "100.00" in credit_str

    def test_entry_with_different_account_types(self):
        """Test entries work with all account types."""
        amount = Money(amount=Decimal("100.00"))

        # Test with each account type
        asset_account = Account("Bank", AccountType.ASSET, "1009", TEST_USER_ID)
        liability_account = Account(
            "Credit Card", AccountType.LIABILITY, "2000", TEST_USER_ID
        )
        equity_account = Account(
            "Owner Equity", AccountType.EQUITY, "3000", TEST_USER_ID
        )
        income_account = Account("Salary", AccountType.INCOME, "4002", TEST_USER_ID)
        expense_account = Account("Rent", AccountType.EXPENSE, "5000", TEST_USER_ID)

        # All should work with both debits and credits
        accounts = [
            asset_account,
            liability_account,
            equity_account,
            income_account,
            expense_account,
        ]

        for account in accounts:
            debit_entry = JournalEntry(account, debit=amount)
            credit_entry = JournalEntry(account, credit=amount)

            assert debit_entry.account == account
            assert credit_entry.account == account
            assert debit_entry.is_debit() is True
            assert credit_entry.is_credit() is True

    def test_entry_immutable_properties(self):
        """Test that entry properties cannot be changed after creation."""
        account = Account("Test", AccountType.ASSET, "1010", TEST_USER_ID)
        amount = Money(amount=Decimal("100.00"))
        entry = JournalEntry(account, debit=amount)

        original_id = entry.id
        original_account = entry.account
        original_debit = entry.debit
        original_credit = entry.credit

        # These should remain unchanged
        assert entry.id == original_id
        assert entry.account == original_account
        assert entry.debit == original_debit
        assert entry.credit == original_credit
