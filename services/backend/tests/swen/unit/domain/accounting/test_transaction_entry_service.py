"""Unit tests for TransactionEntryService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.services import TransactionEntryService
from swen.domain.accounting.value_objects import Currency, Money


# Test fixtures
@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def checking_account(user_id):
    """Asset account (bank checking)."""
    return Account(
        name="Checking Account",
        account_type=AccountType.ASSET,
        account_number="1000",
        user_id=user_id,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def credit_card_account(user_id):
    """Liability account (credit card)."""
    return Account(
        name="VISA Credit Card",
        account_type=AccountType.LIABILITY,
        account_number="2100",
        user_id=user_id,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def groceries_expense(user_id):
    """Expense account."""
    return Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="4100",
        user_id=user_id,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def salary_income(user_id):
    """Income account."""
    return Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="8100",
        user_id=user_id,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def savings_account(user_id):
    """Another asset account for transfers."""
    return Account(
        name="Savings Account",
        account_type=AccountType.ASSET,
        account_number="1100",
        user_id=user_id,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def amount():
    return Money(Decimal("50.00"), Currency("EUR"))


class TestBuildSimpleEntries:
    """Tests for build_simple_entries - expense and income transactions."""

    def test_expense_creates_debit_expense_credit_asset(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """Expense: Debit expense account, Credit asset account."""
        entries = TransactionEntryService.build_simple_entries(
            payment_account=checking_account,
            category_account=groceries_expense,
            amount=amount,
            is_expense=True,
        )

        assert len(entries) == 2

        # First entry: Debit expense
        assert entries[0].account_id == groceries_expense.id
        assert entries[0].debit == Decimal("50.00")
        assert entries[0].credit is None

        # Second entry: Credit asset
        assert entries[1].account_id == checking_account.id
        assert entries[1].debit is None
        assert entries[1].credit == Decimal("50.00")

    def test_income_creates_debit_asset_credit_income(
        self,
        checking_account,
        salary_income,
        amount,
    ):
        """Income: Debit asset account, Credit income account."""
        entries = TransactionEntryService.build_simple_entries(
            payment_account=checking_account,
            category_account=salary_income,
            amount=amount,
            is_expense=False,
        )

        assert len(entries) == 2

        # First entry: Debit asset
        assert entries[0].account_id == checking_account.id
        assert entries[0].debit == Decimal("50.00")
        assert entries[0].credit is None

        # Second entry: Credit income
        assert entries[1].account_id == salary_income.id
        assert entries[1].debit is None
        assert entries[1].credit == Decimal("50.00")

    def test_expense_with_liability_payment(
        self,
        credit_card_account,
        groceries_expense,
        amount,
    ):
        """Expense with credit card: Debit expense, Credit liability."""
        entries = TransactionEntryService.build_simple_entries(
            payment_account=credit_card_account,
            category_account=groceries_expense,
            amount=amount,
            is_expense=True,
        )

        assert len(entries) == 2
        assert entries[0].account_id == groceries_expense.id
        assert entries[0].debit == Decimal("50.00")
        assert entries[0].credit is None
        assert entries[1].account_id == credit_card_account.id
        assert entries[1].debit is None
        assert entries[1].credit == Decimal("50.00")

    def test_rejects_invalid_payment_account_type(
        self,
        groceries_expense,
        salary_income,
        amount,
    ):
        """Payment account must be Asset or Liability."""
        with pytest.raises(InvalidAccountTypeError, match="asset.*liability"):
            TransactionEntryService.build_simple_entries(
                payment_account=groceries_expense,  # Wrong type!
                category_account=salary_income,
                amount=amount,
                is_expense=False,
            )

    def test_rejects_mismatched_category_for_expense(
        self,
        checking_account,
        salary_income,
        amount,
    ):
        """Expense direction requires Expense account type."""
        with pytest.raises(InvalidAccountTypeError, match="expense"):
            TransactionEntryService.build_simple_entries(
                payment_account=checking_account,
                category_account=salary_income,  # Wrong type for expense!
                amount=amount,
                is_expense=True,
            )

    def test_rejects_mismatched_category_for_income(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """Income direction requires Income account type."""
        with pytest.raises(InvalidAccountTypeError, match="income"):
            TransactionEntryService.build_simple_entries(
                payment_account=checking_account,
                category_account=groceries_expense,  # Wrong type for income!
                amount=amount,
                is_expense=False,
            )
