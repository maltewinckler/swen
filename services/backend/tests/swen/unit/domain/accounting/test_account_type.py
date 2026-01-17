"""Tests for the AccountType enumeration."""

from swen.domain.accounting.entities import AccountType


class TestAccountType:
    """Test cases for AccountType enumeration."""

    def test_account_type_values(self):
        """Test that all account types have correct values."""
        assert AccountType.ASSET.value == "asset"
        assert AccountType.LIABILITY.value == "liability"
        assert AccountType.EQUITY.value == "equity"
        assert AccountType.INCOME.value == "income"
        assert AccountType.EXPENSE.value == "expense"

    def test_account_type_completeness(self):
        """Test that all fundamental accounting account types are present."""
        expected_types = {"asset", "liability", "equity", "income", "expense"}
        actual_types = {account_type.value for account_type in AccountType}
        assert actual_types == expected_types

    def test_account_type_enumeration(self):
        """Test enumeration behavior."""
        # Test that we can iterate over all types
        all_types = list(AccountType)
        assert len(all_types) == 5

        # Test that each type is unique
        values = [account_type.value for account_type in all_types]
        assert len(values) == len(set(values))

    def test_account_type_equality(self):
        """Test account type equality."""
        assert AccountType.ASSET == AccountType.ASSET
        assert AccountType.ASSET != AccountType.LIABILITY

    def test_account_type_string_representation(self):
        """Test string representation of account types."""
        assert str(AccountType.ASSET) == "AccountType.ASSET"
        assert repr(AccountType.ASSET) == "<AccountType.ASSET: 'asset'>"

    def test_account_type_from_value(self):
        """Test creating account types from string values."""
        assert AccountType("asset") == AccountType.ASSET
        assert AccountType("liability") == AccountType.LIABILITY
        assert AccountType("equity") == AccountType.EQUITY
        assert AccountType("income") == AccountType.INCOME
        assert AccountType("expense") == AccountType.EXPENSE

    def test_double_entry_bookkeeping_categories(self):
        """Test that account types cover all double-entry bookkeeping categories."""
        # These are the fundamental categories in double-entry bookkeeping
        debit_normal_types = {AccountType.ASSET, AccountType.EXPENSE}
        credit_normal_types = {
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.INCOME,
        }

        all_types = set(AccountType)
        assert debit_normal_types.union(credit_normal_types) == all_types
        assert debit_normal_types.intersection(credit_normal_types) == set()

    def test_account_type_membership(self):
        """Test membership testing with account types."""
        asset_types = [AccountType.ASSET]
        assert AccountType.ASSET in asset_types
        assert AccountType.LIABILITY not in asset_types

        all_types = list(AccountType)
        assert AccountType.ASSET in all_types
        assert AccountType.LIABILITY in all_types

    def test_is_debit_normal_asset(self):
        """Test that ASSET accounts are debit-normal."""
        assert AccountType.ASSET.is_debit_normal() is True

    def test_is_debit_normal_expense(self):
        """Test that EXPENSE accounts are debit-normal."""
        assert AccountType.EXPENSE.is_debit_normal() is True

    def test_is_debit_normal_liability(self):
        """Test that LIABILITY accounts are credit-normal (not debit-normal)."""
        assert AccountType.LIABILITY.is_debit_normal() is False

    def test_is_debit_normal_equity(self):
        """Test that EQUITY accounts are credit-normal (not debit-normal)."""
        assert AccountType.EQUITY.is_debit_normal() is False

    def test_is_debit_normal_income(self):
        """Test that INCOME accounts are credit-normal (not debit-normal)."""
        assert AccountType.INCOME.is_debit_normal() is False

    def test_debit_normal_consistency(self):
        """Test consistency between debit-normal classification and double-entry."""
        debit_normal_types = [
            account_type
            for account_type in AccountType
            if account_type.is_debit_normal()
        ]
        credit_normal_types = [
            account_type
            for account_type in AccountType
            if not account_type.is_debit_normal()
        ]

        # Debit-normal should be Assets and Expenses
        assert set(debit_normal_types) == {AccountType.ASSET, AccountType.EXPENSE}

        # Credit-normal should be Liabilities, Equity, and Income
        assert set(credit_normal_types) == {
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.INCOME,
        }

        # All account types should be classified
        all_types_count = len(list(AccountType))
        assert len(debit_normal_types) + len(credit_normal_types) == all_types_count
