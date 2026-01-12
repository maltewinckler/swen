"""Unit tests for TransactionEntryService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.services import (
    EntrySpec,
    TransactionDirection,
    TransactionEntryService,
)
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
            direction=TransactionDirection.EXPENSE,
        )

        assert len(entries) == 2

        # First entry: Debit expense
        assert entries[0].account == groceries_expense
        assert entries[0].amount == amount
        assert entries[0].is_debit is True

        # Second entry: Credit asset
        assert entries[1].account == checking_account
        assert entries[1].amount == amount
        assert entries[1].is_debit is False
        assert entries[1].is_credit is True

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
            direction=TransactionDirection.INCOME,
        )

        assert len(entries) == 2

        # First entry: Debit asset
        assert entries[0].account == checking_account
        assert entries[0].amount == amount
        assert entries[0].is_debit is True

        # Second entry: Credit income
        assert entries[1].account == salary_income
        assert entries[1].amount == amount
        assert entries[1].is_credit is True

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
            direction=TransactionDirection.EXPENSE,
        )

        assert len(entries) == 2
        assert entries[0].account == groceries_expense
        assert entries[0].is_debit is True
        assert entries[1].account == credit_card_account
        assert entries[1].is_credit is True

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
                direction=TransactionDirection.INCOME,
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
                direction=TransactionDirection.EXPENSE,
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
                direction=TransactionDirection.INCOME,
            )


class TestBuildCategorySwapEntries:
    """Tests for build_category_swap_entries - recategorization."""

    def test_swap_to_expense_creates_both_entries(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """Swapping to expense creates debit expense and credit payment."""
        entries = TransactionEntryService.build_category_swap_entries(
            new_category=groceries_expense,
            payment_account=checking_account,
            amount=amount,
            payment_preserved=False,
        )

        assert len(entries) == 2
        assert entries[0].account == groceries_expense
        assert entries[0].is_debit is True
        assert entries[1].account == checking_account
        assert entries[1].is_credit is True

    def test_swap_to_income_creates_both_entries(
        self,
        checking_account,
        salary_income,
        amount,
    ):
        """Swapping to income creates debit payment and credit income."""
        entries = TransactionEntryService.build_category_swap_entries(
            new_category=salary_income,
            payment_account=checking_account,
            amount=amount,
            payment_preserved=False,
        )

        assert len(entries) == 2
        assert entries[0].account == checking_account
        assert entries[0].is_debit is True
        assert entries[1].account == salary_income
        assert entries[1].is_credit is True

    def test_swap_with_payment_preserved_only_category(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """When payment is preserved (bank import), only category entry created."""
        entries = TransactionEntryService.build_category_swap_entries(
            new_category=groceries_expense,
            payment_account=checking_account,
            amount=amount,
            payment_preserved=True,  # Bank import case
        )

        assert len(entries) == 1
        assert entries[0].account == groceries_expense
        assert entries[0].is_debit is True

    def test_swap_income_with_payment_preserved(
        self,
        checking_account,
        salary_income,
        amount,
    ):
        """Income swap with preserved payment only creates income entry."""
        entries = TransactionEntryService.build_category_swap_entries(
            new_category=salary_income,
            payment_account=checking_account,
            amount=amount,
            payment_preserved=True,
        )

        assert len(entries) == 1
        assert entries[0].account == salary_income
        assert entries[0].is_credit is True

    def test_rejects_non_category_account(
        self,
        checking_account,
        savings_account,
        amount,
    ):
        """Category must be Expense or Income."""
        with pytest.raises(InvalidAccountTypeError, match="expense.*income"):
            TransactionEntryService.build_category_swap_entries(
                new_category=savings_account,  # Asset, not category!
                payment_account=checking_account,
                amount=amount,
            )


class TestBuildInternalTransferEntries:
    """Tests for build_internal_transfer_entries - asset-to-asset transfers."""

    def test_creates_debit_destination_credit_source(
        self,
        checking_account,
        savings_account,
        amount,
    ):
        """Transfer: Debit destination, Credit source."""
        entries = TransactionEntryService.build_internal_transfer_entries(
            source_account=checking_account,
            destination_account=savings_account,
            amount=amount,
            source_preserved=False,
        )

        assert len(entries) == 2
        assert entries[0].account == savings_account  # Destination
        assert entries[0].is_debit is True
        assert entries[1].account == checking_account  # Source
        assert entries[1].is_credit is True

    def test_source_preserved_only_destination_entry(
        self,
        checking_account,
        savings_account,
        amount,
    ):
        """When source preserved (bank import), only destination entry created."""
        entries = TransactionEntryService.build_internal_transfer_entries(
            source_account=checking_account,
            destination_account=savings_account,
            amount=amount,
            source_preserved=True,
        )

        assert len(entries) == 1
        assert entries[0].account == savings_account
        assert entries[0].is_debit is True


class TestBuildLiabilityPaymentEntries:
    """Tests for build_liability_payment_entries."""

    def test_payment_out_debit_liability_credit_asset(
        self,
        checking_account,
        credit_card_account,
        amount,
    ):
        """Payment to liability: Debit liability (reduce debt), Credit asset."""
        entries = TransactionEntryService.build_liability_payment_entries(
            asset_account=checking_account,
            liability_account=credit_card_account,
            amount=amount,
            is_payment_out=True,
            asset_preserved=False,
        )

        assert len(entries) == 2
        assert entries[0].account == credit_card_account
        assert entries[0].is_debit is True  # Reduces liability
        assert entries[1].account == checking_account
        assert entries[1].is_credit is True  # Reduces asset

    def test_payout_debit_asset_credit_liability(
        self,
        checking_account,
        credit_card_account,
        amount,
    ):
        """Payout from liability: Debit asset (increase), Credit liability."""
        entries = TransactionEntryService.build_liability_payment_entries(
            asset_account=checking_account,
            liability_account=credit_card_account,
            amount=amount,
            is_payment_out=False,  # Receiving money (e.g., refund)
            asset_preserved=False,
        )

        assert len(entries) == 2
        assert entries[0].account == checking_account
        assert entries[0].is_debit is True  # Increases asset
        assert entries[1].account == credit_card_account
        assert entries[1].is_credit is True  # Increases liability

    def test_payment_with_asset_preserved(
        self,
        checking_account,
        credit_card_account,
        amount,
    ):
        """When asset preserved (bank import), only liability entry created."""
        entries = TransactionEntryService.build_liability_payment_entries(
            asset_account=checking_account,
            liability_account=credit_card_account,
            amount=amount,
            is_payment_out=True,
            asset_preserved=True,
        )

        assert len(entries) == 1
        assert entries[0].account == credit_card_account
        assert entries[0].is_debit is True


class TestDetermineDirectionFromAmount:
    """Tests for determine_direction_from_amount."""

    def test_negative_amount_is_expense(self):
        """Negative amount = expense."""
        amount = Money(Decimal("-50.00"), Currency("EUR"))
        direction = TransactionEntryService.determine_direction_from_amount(amount)
        assert direction == TransactionDirection.EXPENSE

    def test_positive_amount_is_income(self):
        """Positive amount = income."""
        amount = Money(Decimal("100.00"), Currency("EUR"))
        direction = TransactionEntryService.determine_direction_from_amount(amount)
        assert direction == TransactionDirection.INCOME

    def test_zero_amount_is_income(self):
        """Zero amount treated as income (edge case)."""
        amount = Money(Decimal("0.00"), Currency("EUR"))
        direction = TransactionEntryService.determine_direction_from_amount(amount)
        assert direction == TransactionDirection.INCOME


class TestFindEntries:
    """Tests for find_payment_entry and find_category_entry."""

    def test_find_payment_entry_asset(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """Finds asset account as payment entry."""
        entries = [
            EntrySpec(account=groceries_expense, amount=amount, is_debit=True),
            EntrySpec(account=checking_account, amount=amount, is_debit=False),
        ]

        payment = TransactionEntryService.find_payment_entry(entries)
        assert payment is not None
        assert payment.account == checking_account

    def test_find_payment_entry_liability(
        self,
        credit_card_account,
        groceries_expense,
        amount,
    ):
        """Finds liability account as payment entry."""
        entries = [
            EntrySpec(account=groceries_expense, amount=amount, is_debit=True),
            EntrySpec(account=credit_card_account, amount=amount, is_debit=False),
        ]

        payment = TransactionEntryService.find_payment_entry(entries)
        assert payment is not None
        assert payment.account == credit_card_account

    def test_find_payment_entry_none(self, groceries_expense, salary_income, amount):
        """Returns None when no payment account found."""
        entries = [
            EntrySpec(account=groceries_expense, amount=amount, is_debit=True),
            EntrySpec(account=salary_income, amount=amount, is_debit=False),
        ]

        payment = TransactionEntryService.find_payment_entry(entries)
        assert payment is None

    def test_find_category_entry(
        self,
        checking_account,
        groceries_expense,
        amount,
    ):
        """Finds expense or income as category entry."""
        entries = [
            EntrySpec(account=groceries_expense, amount=amount, is_debit=True),
            EntrySpec(account=checking_account, amount=amount, is_debit=False),
        ]

        category = TransactionEntryService.find_category_entry(entries)
        assert category is not None
        assert category.account == groceries_expense


class TestEntrySpec:
    """Tests for EntrySpec dataclass."""

    def test_is_credit_property(self, checking_account, amount):
        """is_credit is inverse of is_debit."""
        debit_entry = EntrySpec(account=checking_account, amount=amount, is_debit=True)
        credit_entry = EntrySpec(
            account=checking_account,
            amount=amount,
            is_debit=False,
        )

        assert debit_entry.is_credit is False
        assert credit_entry.is_credit is True

    def test_repr(self, checking_account, amount):
        """EntrySpec has readable repr."""
        entry = EntrySpec(account=checking_account, amount=amount, is_debit=True)
        assert "Dr" in repr(entry)
        assert "Checking Account" in repr(entry)

        credit_entry = EntrySpec(account=checking_account, amount=amount, is_debit=False)
        assert "Cr" in repr(credit_entry)
