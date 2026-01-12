"""Tests for the Transaction aggregate and double-entry bookkeeping logic."""

from decimal import Decimal
from uuid import uuid4

import pytest
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import (
    EmptyTransactionError,
    TransactionAlreadyPostedError,
    UnbalancedTransactionError,
    UnsupportedCurrencyError,
    ZeroAmountError,
)
from swen.domain.accounting.value_objects import (
    Money,
    TransactionMetadata,
    TransactionSource,
)

# Test user ID for all transaction tests
TEST_USER_ID = uuid4()


class TestTransaction:
    """Test cases for Transaction aggregate."""

    def test_simple_expense_transaction(self):
        """Test creating a simple expense transaction."""
        # Create accounts
        checking = Account("Checking Account", AccountType.ASSET, "1000", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5000", TEST_USER_ID)

        # Create transaction
        transaction = Transaction("Grocery shopping at REWE", TEST_USER_ID)

        # Add entries: Debit Expense (groceries), Credit Asset (checking)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Post the transaction
        transaction.post()

        # Verify transaction is posted and balanced
        assert transaction.is_posted
        assert len(transaction.entries) == 2
        assert transaction.total_amount() == amount
        assert transaction.user_id == TEST_USER_ID

    def test_income_transaction(self):
        """Test creating an income transaction."""
        # Create accounts
        checking = Account("Checking Account", AccountType.ASSET, "1001", TEST_USER_ID)
        salary = Account("Salary Income", AccountType.INCOME, "4000", TEST_USER_ID)

        # Create transaction
        transaction = Transaction("Monthly salary", TEST_USER_ID)

        # Add entries: Debit Asset (checking), Credit Income (salary)
        amount = Money(amount=Decimal("3000.00"))
        transaction.add_debit(checking, amount)
        transaction.add_credit(salary, amount)

        # Post the transaction
        transaction.post()

        # Verify
        assert transaction.is_posted
        assert transaction.involves_account(checking)
        assert transaction.involves_account(salary)

    def test_transaction_validation_requires_minimum_entries(self):
        """Test that transactions require at least 2 entries."""
        transaction = Transaction("Invalid transaction", TEST_USER_ID)

        # Try to post with no entries
        with pytest.raises(EmptyTransactionError):
            transaction.post()

        # Try to post with only one entry
        checking = Account("Checking", AccountType.ASSET, "1002", TEST_USER_ID)
        transaction.add_debit(checking, Money(amount=Decimal("100.00")))

        with pytest.raises(EmptyTransactionError):
            transaction.post()

    def test_transaction_validation_requires_balance(self):
        """Test that transactions must be balanced (debits = credits)."""
        checking = Account("Checking", AccountType.ASSET, "1003", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5001", TEST_USER_ID)

        transaction = Transaction("Unbalanced transaction", TEST_USER_ID)

        # Add unbalanced entries
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(
            checking,
            Money(amount=Decimal("30.00")),
        )  # Wrong amount!

        with pytest.raises(UnbalancedTransactionError):
            transaction.post()

    def test_transaction_rejects_zero_amount_entries(self):
        """Zero-amount journal entries should be rejected (ambiguous debit/credit)."""
        checking = Account("Checking", AccountType.ASSET, "2001", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "6001", TEST_USER_ID)
        transaction = Transaction("Zero amount", TEST_USER_ID)
        with pytest.raises(ZeroAmountError):
            transaction.add_debit(groceries, Money(amount=Decimal("0.00")))

    def test_transaction_rejects_non_eur_currency_in_mvp(self):
        """MVP guard: posting non-EUR transactions should raise a clear error."""
        checking = Account("Checking", AccountType.ASSET, "2002", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "6002", TEST_USER_ID)
        transaction = Transaction("Non-EUR", TEST_USER_ID)
        usd = Money(amount=Decimal("10.00"), currency="USD")
        transaction.add_debit(groceries, usd)
        transaction.add_credit(checking, usd)
        with pytest.raises(UnsupportedCurrencyError):
            transaction.post()

    def test_posted_transaction_immutable(self):
        """Test that posted transactions cannot be modified."""
        checking = Account("Checking", AccountType.ASSET, "1004", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5002", TEST_USER_ID)

        transaction = Transaction("Posted transaction", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)
        transaction.post()

        # Try to modify posted transaction
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.add_debit(groceries, Money(amount=Decimal("10.00")))

        with pytest.raises(TransactionAlreadyPostedError):
            transaction.clear_entries()

    def test_complex_transaction_multiple_entries(self):
        """Test transaction with multiple entries (split transaction)."""
        # Create accounts
        checking = Account("Checking", AccountType.ASSET, "1005", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5003", TEST_USER_ID)
        gas = Account("Gas", AccountType.EXPENSE, "5004", TEST_USER_ID)

        # Create split transaction
        transaction = Transaction("Weekly shopping trip", TEST_USER_ID)

        # Split expenses: $30 groceries + $20 gas = $50 total from checking
        transaction.add_debit(groceries, Money(amount=Decimal("30.00")))
        transaction.add_debit(gas, Money(amount=Decimal("20.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))

        # Post transaction
        transaction.post()

        # Verify
        assert transaction.is_posted
        assert len(transaction.entries) == 3
        assert transaction.total_amount() == Money(amount=Decimal("50.00"))

        # Verify account-specific entries
        checking_entries = transaction.get_entries_for_account(checking)
        assert len(checking_entries) == 1
        assert checking_entries[0].is_credit()
        assert checking_entries[0].credit == Money(amount=Decimal("50.00"))

    def test_transaction_reversal_concept(self):
        """Test the concept of transaction reversal."""
        # Original transaction
        checking = Account("Checking", AccountType.ASSET, "1006", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5005", TEST_USER_ID)

        original = Transaction("Original purchase", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        original.add_debit(groceries, amount)
        original.add_credit(checking, amount)
        original.post()

        # Create reversal manually (in real system, this would be a domain service)
        reversal = Transaction("Reversal of original purchase", TEST_USER_ID)
        reversal.add_credit(groceries, amount)  # Reverse: credit the expense
        reversal.add_debit(checking, amount)  # Reverse: debit the asset
        reversal.post()

        # Both transactions should be valid and posted
        assert original.is_posted
        assert reversal.is_posted

        # The reversal should have opposite entries
        orig_groc_entry = next(e for e in original.entries if e.account == groceries)
        rev_groc_entry = next(e for e in reversal.entries if e.account == groceries)

        assert orig_groc_entry.is_debit()
        assert rev_groc_entry.is_credit()

    def test_transaction_string_representation(self):
        """Test string representation of transactions."""
        transaction = Transaction("Test transaction", TEST_USER_ID)
        assert "DRAFT" in str(transaction)
        assert "Test transaction" in str(transaction)

        # Add entries and post
        checking = Account("Checking", AccountType.ASSET, "1007", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5006", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))

        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)
        transaction.post()

        transaction_str = str(transaction)
        assert "POSTED" in transaction_str
        assert "Test transaction" in transaction_str
        assert "2 entries" in transaction_str

    def test_transaction_with_quantized_money_amounts(self):
        """Test transactions work with Money amounts requiring quantization."""
        # Create accounts
        checking = Account("Checking", AccountType.ASSET, "1008", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5007", TEST_USER_ID)

        # Create transaction with amounts that would need quantization
        transaction = Transaction("Purchase with calculated amounts", TEST_USER_ID)

        # Use Money multiplication that triggers quantization
        base_amount = Money(amount=Decimal("10.00"))
        calculated_amount = base_amount * 2.5  # Results in 25.00 after quantization

        # This should work fine - both amounts are quantized to 2 decimal places
        transaction.add_debit(groceries, calculated_amount)
        transaction.add_credit(checking, calculated_amount)

        # Should post successfully - quantization ensures amounts are equal
        transaction.post()

        # Verify transaction is balanced
        assert transaction.is_posted
        assert transaction.total_amount() == Money(amount=Decimal("25.00"))

        # Test with more complex calculations that could introduce rounding
        transaction2 = Transaction("Complex calculation", TEST_USER_ID)

        # Multiple operations that could introduce precision issues
        amount1 = Money(amount=Decimal("33.33")) * 3  # Should be 99.99
        amount2 = Money(amount=Decimal("50.00")) + Money(
            amount=Decimal("49.99"),
        )  # Should be 99.99

        transaction2.add_debit(groceries, amount1)
        transaction2.add_credit(checking, amount2)

        # This should work because both amounts should quantize to the same value
        transaction2.post()
        assert transaction2.is_posted

    def test_remove_entry_from_draft_transaction(self):
        """Test removing an entry from a draft transaction."""
        checking = Account("Checking", AccountType.ASSET, "1009", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5008", TEST_USER_ID)

        transaction = Transaction("Test removal", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))

        # Get entry ID to remove
        entry_id = transaction.entries[0].id

        # Remove the entry
        transaction.remove_entry(entry_id)

        # Verify entry was removed
        assert len(transaction.entries) == 1
        assert all(e.id != entry_id for e in transaction.entries)

    def test_remove_entry_from_posted_transaction_fails(self):
        """Test that removing an entry from posted transaction raises error."""
        checking = Account("Checking", AccountType.ASSET, "1010", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5009", TEST_USER_ID)

        transaction = Transaction("Posted transaction", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))
        transaction.post()

        entry_id = transaction.entries[0].id

        # Try to remove entry from posted transaction
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.remove_entry(entry_id)

    def test_clear_entries_from_draft_transaction(self):
        """Test clearing all entries from a draft transaction."""
        checking = Account("Checking", AccountType.ASSET, "1011", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5010", TEST_USER_ID)
        gas = Account("Gas", AccountType.EXPENSE, "5011", TEST_USER_ID)

        transaction = Transaction("Test clear", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("30.00")))
        transaction.add_debit(gas, Money(amount=Decimal("20.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))

        # Clear all entries
        transaction.clear_entries()

        # Verify all entries removed
        assert len(transaction.entries) == 0

    def test_clear_entries_from_posted_transaction_fails(self):
        """Test that clearing entries from posted transaction raises error."""
        checking = Account("Checking", AccountType.ASSET, "1012", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5012", TEST_USER_ID)

        transaction = Transaction("Posted transaction", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))
        transaction.post()

        # Try to clear entries from posted transaction
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.clear_entries()

    def test_unpost_transaction(self):
        """Test unposting a transaction makes it mutable again."""
        checking = Account("Checking", AccountType.ASSET, "1013", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5013", TEST_USER_ID)

        transaction = Transaction("Test unpost", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))
        transaction.post()

        assert transaction.is_posted

        # Unpost the transaction
        transaction.unpost()

        # Verify transaction is now mutable
        assert not transaction.is_posted

        # Should be able to modify it now
        transaction.add_debit(groceries, Money(amount=Decimal("10.00")))
        assert len(transaction.entries) == 3

    def test_involves_account_true(self):
        """Test involves_account returns True when account is in transaction."""
        checking = Account("Checking", AccountType.ASSET, "1014", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5014", TEST_USER_ID)
        savings = Account("Savings", AccountType.ASSET, "1015", TEST_USER_ID)

        transaction = Transaction("Test involves", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))

        # Should involve checking and groceries
        assert transaction.involves_account(checking)
        assert transaction.involves_account(groceries)

        # Should not involve savings
        assert not transaction.involves_account(savings)

    def test_involves_account_false(self):
        """Test involves_account returns False when account is not in transaction."""
        checking = Account("Checking", AccountType.ASSET, "1016", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5015", TEST_USER_ID)
        savings = Account("Savings", AccountType.ASSET, "1017", TEST_USER_ID)

        transaction = Transaction("Test involves", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))

        # Should not involve savings
        assert not transaction.involves_account(savings)

    def test_transaction_equality(self):
        """Test transaction equality based on ID."""
        transaction1 = Transaction("Transaction 1", TEST_USER_ID)
        transaction2 = Transaction("Transaction 2", TEST_USER_ID)
        transaction3 = transaction1

        # Same object should be equal
        assert transaction1 == transaction3

        # Different transactions should not be equal
        assert transaction1 != transaction2

        # Transaction should not equal non-transaction
        assert transaction1 != "not a transaction"
        assert transaction1 != 123

    def test_transaction_hashable(self):
        """Test that transactions are hashable and can be used in sets/dicts."""
        transaction1 = Transaction("Transaction 1", TEST_USER_ID)
        transaction2 = Transaction("Transaction 2", TEST_USER_ID)

        # Should be able to add to set
        transaction_set = {transaction1, transaction2}
        assert len(transaction_set) == 2
        assert transaction1 in transaction_set

        # Should be able to use as dict key
        transaction_dict = {transaction1: "value1", transaction2: "value2"}
        assert transaction_dict[transaction1] == "value1"

    def test_is_balanced_method(self):
        """Test the is_balanced() convenience method."""
        checking = Account("Checking", AccountType.ASSET, "1018", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5016", TEST_USER_ID)

        # Create balanced transaction
        balanced = Transaction("Balanced", TEST_USER_ID)
        balanced.add_debit(groceries, Money(amount=Decimal("50.00")))
        balanced.add_credit(checking, Money(amount=Decimal("50.00")))

        assert balanced.is_balanced() is True

        # Create unbalanced transaction
        unbalanced = Transaction("Unbalanced", TEST_USER_ID)
        unbalanced.add_debit(groceries, Money(amount=Decimal("50.00")))
        unbalanced.add_credit(checking, Money(amount=Decimal("30.00")))

        assert unbalanced.is_balanced() is False

        # Empty transaction is not balanced
        empty = Transaction("Empty", TEST_USER_ID)
        assert empty.is_balanced() is False

    def test_post_already_posted_transaction_fails(self):
        """Test that posting an already posted transaction raises error."""
        checking = Account("Checking", AccountType.ASSET, "1019", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5017", TEST_USER_ID)

        transaction = Transaction("Already posted", TEST_USER_ID)
        transaction.add_debit(groceries, Money(amount=Decimal("50.00")))
        transaction.add_credit(checking, Money(amount=Decimal("50.00")))
        transaction.post()

        # Try to post again
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.post()


class TestTransactionCounterpartyAndMetadata:
    """Test cases for Transaction counterparty and metadata features."""

    def test_transaction_with_counterparty(self):
        """Test creating a transaction with counterparty information."""
        checking = Account("Checking Account", AccountType.ASSET, "1020", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5018", TEST_USER_ID)

        # Create transaction with counterparty
        transaction = Transaction(
            "Grocery shopping",
            TEST_USER_ID,
            counterparty="REWE MARKT GMBH",
        )

        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)
        transaction.post()

        # Verify counterparty is stored
        assert transaction.counterparty == "REWE MARKT GMBH"
        assert "REWE MARKT GMBH" in str(transaction)

    def test_transaction_with_counterparty_iban(self):
        """Test creating a transaction with counterparty IBAN."""
        checking = Account("Checking Account", AccountType.ASSET, "1021", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5019", TEST_USER_ID)

        # Create transaction with counterparty IBAN
        transaction = Transaction(
            "Grocery shopping",
            TEST_USER_ID,
            counterparty_iban="DE89 3704 0044 0532 0130 00",
        )

        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Verify IBAN is stored and normalized
        assert transaction.counterparty_iban == "DE89370400440532013000"

    def test_transaction_with_metadata(self):
        """Test creating a transaction with metadata tags."""
        checking = Account("Checking Account", AccountType.ASSET, "1022", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5020", TEST_USER_ID)

        # Create transaction and set typed metadata first
        transaction = Transaction("Grocery shopping", TEST_USER_ID)

        # Set typed metadata with source, then add custom keys
        transaction.set_metadata(TransactionMetadata(source=TransactionSource.MANUAL))
        transaction.set_metadata_raw("merchant", "REWE")
        transaction.set_metadata_raw("category_label", "Groceries")
        transaction.set_metadata_raw("project", "Household")

        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Verify metadata is stored
        assert transaction.get_metadata_raw("merchant") == "REWE"
        assert transaction.get_metadata_raw("category_label") == "Groceries"
        assert transaction.get_metadata_raw("project") == "Household"
        assert transaction.has_metadata_raw("merchant")
        assert not transaction.has_metadata_raw("nonexistent")

    def test_set_metadata_on_draft_transaction(self):
        """Test adding metadata to a draft transaction."""
        checking = Account("Checking Account", AccountType.ASSET, "1023", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5021", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Set typed metadata first (source is required for posting)
        transaction.set_metadata(TransactionMetadata(source=TransactionSource.MANUAL))

        # Add custom metadata before posting
        transaction.set_metadata_raw("merchant", "REWE")
        transaction.set_metadata_raw("location", "Berlin")

        assert transaction.get_metadata_raw("merchant") == "REWE"
        assert transaction.get_metadata_raw("location") == "Berlin"

        # Can post with metadata
        transaction.post()
        assert transaction.is_posted

    def test_cannot_modify_metadata_on_posted_transaction(self):
        """Test that metadata cannot be changed after posting."""
        checking = Account("Checking Account", AccountType.ASSET, "1024", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5022", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)
        transaction.post()

        # Try to modify metadata after posting
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.set_metadata_raw("merchant", "REWE")

        with pytest.raises(TransactionAlreadyPostedError):
            transaction.remove_metadata_raw("merchant")

    def test_update_counterparty_on_draft_transaction(self):
        """Test updating counterparty on a draft transaction."""
        checking = Account("Checking Account", AccountType.ASSET, "1025", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5023", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID, counterparty="REWE")
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Update counterparty
        transaction.update_counterparty("REWE MARKT GMBH")
        assert transaction.counterparty == "REWE MARKT GMBH"

    def test_cannot_update_counterparty_on_posted_transaction(self):
        """Test that counterparty cannot be changed after posting."""
        checking = Account("Checking Account", AccountType.ASSET, "1026", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5024", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID, counterparty="REWE")
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)
        transaction.post()

        # Try to update counterparty after posting
        with pytest.raises(TransactionAlreadyPostedError):
            transaction.update_counterparty("ALDI")

    def test_remove_metadata(self):
        """Test removing metadata from a draft transaction."""
        checking = Account("Checking Account", AccountType.ASSET, "1027", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5025", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Add and remove metadata
        transaction.set_metadata_raw("temp_tag", "temporary")
        assert transaction.has_metadata_raw("temp_tag")

        transaction.remove_metadata_raw("temp_tag")
        assert not transaction.has_metadata_raw("temp_tag")

    def test_metadata_in_string_representation(self):
        """Test that metadata appears in string representation."""
        checking = Account("Checking Account", AccountType.ASSET, "1028", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5026", TEST_USER_ID)

        transaction = Transaction(
            "Grocery shopping",
            TEST_USER_ID,
            counterparty="REWE",
        )
        # Set typed metadata first, then add custom keys for display
        transaction.set_metadata(TransactionMetadata(source=TransactionSource.MANUAL))
        transaction.set_metadata_raw("merchant", "REWE")
        transaction.set_metadata_raw("category", "Groceries")

        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        str_repr = str(transaction)
        assert "REWE" in str_repr
        assert "merchant=REWE" in str_repr
        assert "category=Groceries" in str_repr

    def test_get_metadata_with_default(self):
        """Test getting metadata with default value."""
        checking = Account("Checking Account", AccountType.ASSET, "1029", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5027", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID)
        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Get non-existent metadata with default
        assert transaction.get_metadata_raw("nonexistent", "default") == "default"
        assert transaction.get_metadata_raw("nonexistent") is None

    def test_metadata_raw_defensive_copy(self):
        """Test that metadata_raw property returns a defensive copy."""
        checking = Account("Checking Account", AccountType.ASSET, "1030", TEST_USER_ID)
        groceries = Account("Groceries", AccountType.EXPENSE, "5028", TEST_USER_ID)

        transaction = Transaction("Grocery shopping", TEST_USER_ID)
        transaction.set_metadata(TransactionMetadata(source=TransactionSource.MANUAL))
        transaction.set_metadata_raw("merchant", "REWE")

        amount = Money(amount=Decimal("50.00"))
        transaction.add_debit(groceries, amount)
        transaction.add_credit(checking, amount)

        # Modify the returned raw metadata dict
        metadata_copy = transaction.metadata_raw
        metadata_copy["hacked"] = "value"

        # Original should be unchanged
        assert not transaction.has_metadata_raw("hacked")
        assert "hacked" not in transaction.metadata_raw
