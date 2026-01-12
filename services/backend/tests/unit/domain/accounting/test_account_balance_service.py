"""Tests for the AccountBalanceService domain service."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from swen.domain.accounting.entities import AccountType
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.accounting.value_objects import Money


class TestAccountBalanceService:
    """Test cases for AccountBalanceService."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock accounts with real AccountType instances
        self.checking_account = Mock()
        self.checking_account.id = uuid4()
        self.checking_account.default_currency = "EUR"
        self.checking_account.account_type = AccountType.ASSET  # Debit-normal

        self.income_account = Mock()
        self.income_account.id = uuid4()
        self.income_account.default_currency = "EUR"
        self.income_account.account_type = AccountType.INCOME  # Credit-normal

        self.expense_account = Mock()
        self.expense_account.id = uuid4()
        self.expense_account.default_currency = "EUR"
        self.expense_account.account_type = AccountType.EXPENSE  # Debit-normal

        self.liability_account = Mock()
        self.liability_account.id = uuid4()
        self.liability_account.default_currency = "EUR"
        self.liability_account.account_type = AccountType.LIABILITY  # Credit-normal

    def test_calculate_balance_empty_transactions(self):
        """Test balance calculation with no transactions."""
        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[],
        )

        # Should return zero balance
        assert balance.amount == Decimal(0)
        assert balance.currency == "EUR"

    def test_get_trial_balance_empty_accounts(self):
        """Test trial balance with no accounts."""
        trial_balance = AccountBalanceService.get_trial_balance(
            accounts=[],
            all_transactions=[],
        )

        assert trial_balance == {}

    def test_verify_trial_balance_balanced(self):
        """Test trial balance verification when balanced."""
        # Create a balanced set of account balances
        trial_balance = {
            uuid4(): Money(amount=Decimal("1000.00")),  # Asset (debit normal)
            uuid4(): Money(amount=Decimal("500.00")),  # Expense (debit normal)
            uuid4(): Money(amount=Decimal("-1500.00")),  # Income (credit normal)
        }

        is_balanced = AccountBalanceService.verify_trial_balance(trial_balance)
        assert is_balanced is True

    def test_verify_trial_balance_unbalanced(self):
        """Test trial balance verification when unbalanced."""
        trial_balance = {
            uuid4(): Money(amount=Decimal("1000.00")),
            uuid4(): Money(amount=Decimal("200.00")),  # Doesn't balance
        }

        is_balanced = AccountBalanceService.verify_trial_balance(trial_balance)
        assert is_balanced is False

    def test_verify_trial_balance_empty(self):
        """Test trial balance verification with empty balance."""
        is_balanced = AccountBalanceService.verify_trial_balance({})
        assert is_balanced is True

    def test_verify_trial_balance_different_currencies_error(self):
        """Test that different currencies in trial balance raise error."""
        trial_balance = {
            uuid4(): Money(amount=Decimal("1000.00"), currency="USD"),
            uuid4(): Money(amount=Decimal("500.00"), currency="EUR"),
        }

        with pytest.raises(
            ValueError,
            match="All balances must be in the same currency",
        ):
            AccountBalanceService.verify_trial_balance(trial_balance)

    def test_calculate_balance_debit_normal_account(self):
        """Test balance calculation for debit-normal accounts (Assets/Expenses)."""
        # Create mock transaction with journal entries
        transaction = Mock()
        transaction.date = "2025-01-01"
        transaction.is_posted = True

        # Create debit entry for asset account
        debit_entry = Mock()
        debit_entry.account = self.checking_account
        debit_entry.amount = Money(amount=Decimal("1000.00"))
        debit_entry.is_debit.return_value = True
        debit_entry.is_credit.return_value = False

        transaction.entries = [debit_entry]

        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[transaction],
        )

        # Asset account should increase with debits
        assert balance.amount == Decimal("1000.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_credit_normal_account(self):
        """Test balance calculation for credit-normal accounts."""
        # Create mock transaction with journal entries
        transaction = Mock()
        transaction.date = "2025-01-01"
        transaction.is_posted = True

        # Create credit entry for income account
        credit_entry = Mock()
        credit_entry.account = self.income_account
        credit_entry.amount = Money(amount=Decimal("2000.00"))
        credit_entry.is_debit.return_value = False
        credit_entry.is_credit.return_value = True

        transaction.entries = [credit_entry]

        balance = AccountBalanceService.calculate_balance(
            account=self.income_account,
            transactions=[transaction],
        )

        # Income account should increase with credits
        assert balance.amount == Decimal("2000.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_mixed_entries(self):
        """Test balance calculation with multiple debit and credit entries."""
        # Create multiple transactions
        transaction1 = Mock()
        transaction1.date = "2025-01-01"
        transaction1.is_posted = True

        # Debit entry for checking account
        debit_entry = Mock()
        debit_entry.account = self.checking_account
        debit_entry.amount = Money(amount=Decimal("1000.00"))
        debit_entry.is_debit.return_value = True
        debit_entry.is_credit.return_value = False

        transaction1.entries = [debit_entry]

        transaction2 = Mock()
        transaction2.date = "2025-01-02"
        transaction2.is_posted = True

        # Credit entry for checking account (e.g., payment out)
        credit_entry = Mock()
        credit_entry.account = self.checking_account
        credit_entry.amount = Money(amount=Decimal("300.00"))
        credit_entry.is_debit.return_value = False
        credit_entry.is_credit.return_value = True

        transaction2.entries = [credit_entry]

        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[transaction1, transaction2],
        )

        # Asset account: +1000 (debit) - 300 (credit) = 700
        assert balance.amount == Decimal("700.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_with_unposted_transactions(self):
        """Test that unposted transactions are excluded from balance calculation."""
        # Create posted transaction
        posted_transaction = Mock()
        posted_transaction.date = "2025-01-01"
        posted_transaction.is_posted = True

        posted_entry = Mock()
        posted_entry.account = self.checking_account
        posted_entry.amount = Money(amount=Decimal("1000.00"))
        posted_entry.is_debit.return_value = True
        posted_entry.is_credit.return_value = False

        posted_transaction.entries = [posted_entry]

        # Create unposted transaction
        unposted_transaction = Mock()
        unposted_transaction.date = "2025-01-01"
        unposted_transaction.is_posted = False

        unposted_entry = Mock()
        unposted_entry.account = self.checking_account
        unposted_entry.amount = Money(amount=Decimal("500.00"))
        unposted_entry.is_debit.return_value = True
        unposted_entry.is_credit.return_value = False

        unposted_transaction.entries = [unposted_entry]

        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[posted_transaction, unposted_transaction],
        )

        # Only posted transaction should be included
        assert balance.amount == Decimal("1000.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_with_as_of_date(self):
        """Test balance calculation with as_of_date filtering."""
        # Create transactions with different dates
        old_transaction = Mock()
        old_transaction.date = "2025-01-01"
        old_transaction.is_posted = True

        old_entry = Mock()
        old_entry.account = self.checking_account
        old_entry.amount = Money(amount=Decimal("1000.00"))
        old_entry.is_debit.return_value = True
        old_entry.is_credit.return_value = False

        old_transaction.entries = [old_entry]

        new_transaction = Mock()
        new_transaction.date = "2025-02-15"
        new_transaction.is_posted = True

        new_entry = Mock()
        new_entry.account = self.checking_account
        new_entry.amount = Money(amount=Decimal("500.00"))
        new_entry.is_debit.return_value = True
        new_entry.is_credit.return_value = False

        new_transaction.entries = [new_entry]

        # Calculate balance as of Jan 31 (should only include old transaction)
        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[old_transaction, new_transaction],
            as_of_date="2025-01-31",
        )

        # Should only include the old transaction
        assert balance.amount == Decimal("1000.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_excludes_future_transactions(self):
        """Test that future transactions are excluded when using as_of_date."""
        # Create transactions
        past_transaction = Mock()
        past_transaction.date = "2025-01-15"
        past_transaction.is_posted = True

        past_entry = Mock()
        past_entry.account = self.checking_account
        past_entry.amount = Money(amount=Decimal("1000.00"))
        past_entry.is_debit.return_value = True
        past_entry.is_credit.return_value = False

        past_transaction.entries = [past_entry]

        future_transaction = Mock()
        future_transaction.date = "2025-03-01"
        future_transaction.is_posted = True

        future_entry = Mock()
        future_entry.account = self.checking_account
        future_entry.amount = Money(amount=Decimal("500.00"))
        future_entry.is_debit.return_value = True
        future_entry.is_credit.return_value = False

        future_transaction.entries = [future_entry]

        # Calculate balance as of Feb 1
        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[past_transaction, future_transaction],
            as_of_date="2025-02-01",
        )

        # Should exclude future transaction
        assert balance.amount == Decimal("1000.00")
        assert balance.currency == "EUR"

    def test_calculate_balance_allows_datetime_transactions_and_string_filters(self):
        """Regression test mixing datetime transactions with string filters."""
        transaction = Mock()
        transaction.date = datetime(2025, 2, 10, tzinfo=timezone.utc)
        transaction.is_posted = True

        entry = Mock()
        entry.account = self.checking_account
        entry.amount = Money(amount=Decimal("250.00"))
        entry.is_debit.return_value = True
        entry.is_credit.return_value = False

        transaction.entries = [entry]

        balance = AccountBalanceService.calculate_balance(
            account=self.checking_account,
            transactions=[transaction],
            as_of_date="2025-02-28",  # string filter should work with datetime dates
        )

        assert balance.amount == Decimal("250.00")
        assert balance.currency == "EUR"

    def test_get_trial_balance_with_date_filter(self):
        """Test trial balance calculation with date filtering."""
        # Create accounts
        checking = Mock()
        checking.id = uuid4()
        checking.default_currency = "EUR"
        checking.account_type = AccountType.ASSET

        income = Mock()
        income.id = uuid4()
        income.default_currency = "EUR"
        income.account_type = AccountType.INCOME

        # Create transactions
        jan_transaction = Mock()
        jan_transaction.date = "2025-01-15"
        jan_transaction.is_posted = True

        jan_checking_entry = Mock()
        jan_checking_entry.account = checking
        jan_checking_entry.amount = Money(amount=Decimal("1000.00"))
        jan_checking_entry.is_debit.return_value = True
        jan_checking_entry.is_credit.return_value = False

        jan_income_entry = Mock()
        jan_income_entry.account = income
        jan_income_entry.amount = Money(amount=Decimal("1000.00"))
        jan_income_entry.is_debit.return_value = False
        jan_income_entry.is_credit.return_value = True

        jan_transaction.entries = [jan_checking_entry, jan_income_entry]

        feb_transaction = Mock()
        feb_transaction.date = "2025-02-15"
        feb_transaction.is_posted = True

        feb_checking_entry = Mock()
        feb_checking_entry.account = checking
        feb_checking_entry.amount = Money(amount=Decimal("500.00"))
        feb_checking_entry.is_debit.return_value = True
        feb_checking_entry.is_credit.return_value = False

        feb_income_entry = Mock()
        feb_income_entry.account = income
        feb_income_entry.amount = Money(amount=Decimal("500.00"))
        feb_income_entry.is_debit.return_value = False
        feb_income_entry.is_credit.return_value = True

        feb_transaction.entries = [feb_checking_entry, feb_income_entry]

        # Get trial balance as of Jan 31
        trial_balance = AccountBalanceService.get_trial_balance(
            accounts=[checking, income],
            all_transactions=[jan_transaction, feb_transaction],
            as_of_date="2025-01-31",
        )

        # Should only include January transactions
        # Balances are in signed debit convention:
        # - Asset (debit-normal): positive
        # - Income (credit-normal): negative
        assert trial_balance[checking.id].amount == Decimal("1000.00")
        assert trial_balance[income.id].amount == Decimal("-1000.00")

        # Trial balance should sum to zero (balanced)
        assert AccountBalanceService.verify_trial_balance(trial_balance) is True

    def test_get_trial_balance_with_multiple_accounts(self):
        """Test trial balance with multiple accounts and transactions."""
        # Create multiple accounts
        accounts = []
        for _ in range(3):
            account = Mock()
            account.id = uuid4()
            account.default_currency = "EUR"
            account.account_type = AccountType.ASSET
            accounts.append(account)

        # Create transactions
        transactions = []
        for i, account in enumerate(accounts):
            transaction = Mock()
            transaction.date = "2025-01-01"
            transaction.is_posted = True

            entry = Mock()
            entry.account = account
            entry.amount = Money(amount=Decimal(str((i + 1) * 100)))
            entry.is_debit.return_value = True
            entry.is_credit.return_value = False

            transaction.entries = [entry]
            transactions.append(transaction)

        # Get trial balance
        trial_balance = AccountBalanceService.get_trial_balance(
            accounts=accounts,
            all_transactions=transactions,
        )

        # Verify all accounts are included
        assert len(trial_balance) == 3
        assert trial_balance[accounts[0].id].amount == Decimal("100.00")
        assert trial_balance[accounts[1].id].amount == Decimal("200.00")
        assert trial_balance[accounts[2].id].amount == Decimal("300.00")

    def test_trial_balance_with_balanced_double_entry(self):
        """Test that a proper double-entry transaction results in a balanced trial balance.

        This is the key test for the trial balance fix:
        A balanced entry "Debit Asset 100 / Credit Equity 100" should verify as balanced.
        """
        # Create accounts
        asset = Mock()
        asset.id = uuid4()
        asset.default_currency = "EUR"
        asset.account_type = AccountType.ASSET

        equity = Mock()
        equity.id = uuid4()
        equity.default_currency = "EUR"
        equity.account_type = AccountType.EQUITY

        # Create a balanced double-entry transaction
        transaction = Mock()
        transaction.date = "2025-01-01"
        transaction.is_posted = True

        # Debit Asset 100
        asset_entry = Mock()
        asset_entry.account = asset
        asset_entry.amount = Money(amount=Decimal("100.00"))
        asset_entry.is_debit.return_value = True
        asset_entry.is_credit.return_value = False

        # Credit Equity 100
        equity_entry = Mock()
        equity_entry.account = equity
        equity_entry.amount = Money(amount=Decimal("100.00"))
        equity_entry.is_debit.return_value = False
        equity_entry.is_credit.return_value = True

        transaction.entries = [asset_entry, equity_entry]

        # Get trial balance
        trial_balance = AccountBalanceService.get_trial_balance(
            accounts=[asset, equity],
            all_transactions=[transaction],
        )

        # Asset (debit-normal) should be +100, Equity (credit-normal) should be -100
        assert trial_balance[asset.id].amount == Decimal("100.00")
        assert trial_balance[equity.id].amount == Decimal("-100.00")

        # Trial balance should verify as balanced (sum = 0)
        assert AccountBalanceService.verify_trial_balance(trial_balance) is True

    def test_trial_balance_expense_with_liability_balanced(self):
        """Test trial balance with expense/liability (credit card purchase)."""
        expense = Mock()
        expense.id = uuid4()
        expense.default_currency = "EUR"
        expense.account_type = AccountType.EXPENSE

        liability = Mock()
        liability.id = uuid4()
        liability.default_currency = "EUR"
        liability.account_type = AccountType.LIABILITY

        # Credit card purchase: Debit Expense / Credit Liability
        transaction = Mock()
        transaction.date = "2025-01-01"
        transaction.is_posted = True

        expense_entry = Mock()
        expense_entry.account = expense
        expense_entry.amount = Money(amount=Decimal("50.00"))
        expense_entry.is_debit.return_value = True
        expense_entry.is_credit.return_value = False

        liability_entry = Mock()
        liability_entry.account = liability
        liability_entry.amount = Money(amount=Decimal("50.00"))
        liability_entry.is_debit.return_value = False
        liability_entry.is_credit.return_value = True

        transaction.entries = [expense_entry, liability_entry]

        trial_balance = AccountBalanceService.get_trial_balance(
            accounts=[expense, liability],
            all_transactions=[transaction],
        )

        # Expense (debit-normal) = +50, Liability (credit-normal) = -50
        assert trial_balance[expense.id].amount == Decimal("50.00")
        assert trial_balance[liability.id].amount == Decimal("-50.00")

        # Should be balanced
        assert AccountBalanceService.verify_trial_balance(trial_balance) is True
