"""Unit tests for TransactionListItemDTO."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from swen.application.dtos.accounting.transaction_list_dto import (
    TransactionListItemDTO,
    _determine_amount_and_direction,
    _find_payment_entry,
)
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.value_objects import Currency, Money


@pytest.fixture
def mock_account():
    """Create a mock account."""

    def _create(
        account_type: AccountType = AccountType.ASSET,
        name: str | None = None,
        iban: str | None = None,
    ):
        account = MagicMock()
        account.id = uuid4()
        account.name = name or f"Test {account_type.value}"
        account.account_type = account_type
        account.iban = iban
        account.default_currency = Currency("EUR")
        return account

    return _create


@pytest.fixture
def mock_entry():
    """Create a mock journal entry."""

    def _create(
        account: MagicMock,
        is_debit: bool = True,
        amount: Decimal = Decimal("50.00"),
    ):
        entry = MagicMock()
        entry.id = uuid4()
        entry.account = account

        if is_debit:
            entry.debit = Money(amount, Currency("EUR"))
            entry.credit = Money(Decimal("0"), Currency("EUR"))
            entry.is_debit.return_value = True
        else:
            entry.debit = Money(Decimal("0"), Currency("EUR"))
            entry.credit = Money(amount, Currency("EUR"))
            entry.is_debit.return_value = False

        return entry

    return _create


@pytest.fixture
def mock_metadata():
    """Create a mock transaction metadata."""

    def _create(source_iban: str | None = None):
        metadata = MagicMock()
        metadata.source_iban = source_iban
        return metadata

    return _create


class TestFindPaymentEntry:
    """Tests for _find_payment_entry helper."""

    def test_finds_asset_account(self, mock_account, mock_entry, mock_metadata):
        """Finds asset account entry as payment entry."""
        asset = mock_account(AccountType.ASSET, "Checking")
        expense = mock_account(AccountType.EXPENSE, "Groceries")

        asset_entry = mock_entry(asset, is_debit=True)
        expense_entry = mock_entry(expense, is_debit=True)

        txn = MagicMock()
        txn.entries = [expense_entry, asset_entry]
        txn.source_iban = None  # source_iban is now a first-class field
        txn.metadata = mock_metadata()

        result = _find_payment_entry(txn)
        assert result == asset_entry

    def test_finds_liability_account(self, mock_account, mock_entry, mock_metadata):
        """Finds liability account entry as payment entry (credit card)."""
        liability = mock_account(AccountType.LIABILITY, "Credit Card")
        expense = mock_account(AccountType.EXPENSE, "Groceries")

        liability_entry = mock_entry(liability, is_debit=False)
        expense_entry = mock_entry(expense, is_debit=True)

        txn = MagicMock()
        txn.entries = [expense_entry, liability_entry]
        txn.source_iban = None  # source_iban is now a first-class field
        txn.metadata = mock_metadata()

        result = _find_payment_entry(txn)
        assert result == liability_entry

    def test_matches_source_iban(self, mock_account, mock_entry, mock_metadata):
        """Uses source_iban (first-class field) to identify payment entry."""
        iban = "DE89370400440532013000"
        checking = mock_account(AccountType.ASSET, "Checking", iban=iban)
        savings = mock_account(
            AccountType.ASSET, "Savings", iban="DE12345678901234567890"
        )

        checking_entry = mock_entry(checking, is_debit=True)
        savings_entry = mock_entry(savings, is_debit=False)

        txn = MagicMock()
        txn.entries = [savings_entry, checking_entry]
        txn.source_iban = iban  # source_iban is now a first-class field
        txn.metadata = mock_metadata()

        result = _find_payment_entry(txn)
        assert result == checking_entry

    def test_falls_back_to_first_entry_if_no_payment_account(
        self,
        mock_account,
        mock_entry,
        mock_metadata,
    ):
        """Falls back to first entry if no payment account found."""
        expense1 = mock_account(AccountType.EXPENSE, "Groceries")
        expense2 = mock_account(AccountType.EXPENSE, "Restaurant")

        entry1 = mock_entry(expense1, is_debit=True)
        entry2 = mock_entry(expense2, is_debit=True)

        txn = MagicMock()
        txn.entries = [entry1, entry2]
        txn.source_iban = None  # source_iban is now a first-class field
        txn.metadata = mock_metadata()

        result = _find_payment_entry(txn)
        assert result == entry1


class TestDetermineAmountAndDirection:
    """Tests for _determine_amount_and_direction helper."""

    def test_asset_debit_is_income(self, mock_account, mock_entry):
        """Debit to asset account is income (money coming in)."""
        asset = mock_account(AccountType.ASSET, "Checking")
        entry = mock_entry(asset, is_debit=True, amount=Decimal("100.00"))

        amount, currency, is_income = _determine_amount_and_direction(entry)

        assert amount == Decimal("100.00")
        assert currency == "EUR"
        assert is_income is True

    def test_asset_credit_is_expense(self, mock_account, mock_entry):
        """Credit to asset account is expense (money going out)."""
        asset = mock_account(AccountType.ASSET, "Checking")
        entry = mock_entry(asset, is_debit=False, amount=Decimal("50.00"))

        amount, currency, is_income = _determine_amount_and_direction(entry)

        assert amount == Decimal("50.00")
        assert currency == "EUR"
        assert is_income is False

    def test_liability_credit_is_expense_like(self, mock_account, mock_entry):
        """Credit to liability is expense-like (new debt from spending)."""
        liability = mock_account(AccountType.LIABILITY, "Credit Card")
        entry = mock_entry(liability, is_debit=False, amount=Decimal("75.00"))

        amount, currency, is_income = _determine_amount_and_direction(entry)

        assert amount == Decimal("75.00")
        assert currency == "EUR"
        assert is_income is False  # Spending on credit card

    def test_liability_debit_is_income_like(self, mock_account, mock_entry):
        """Debit to liability is income-like (paying off debt)."""
        liability = mock_account(AccountType.LIABILITY, "Credit Card")
        entry = mock_entry(liability, is_debit=True, amount=Decimal("200.00"))

        amount, currency, is_income = _determine_amount_and_direction(entry)

        assert amount == Decimal("200.00")
        assert currency == "EUR"
        assert is_income is True  # Paying off credit card


class TestTransactionListItemDTO:
    """Tests for TransactionListItemDTO.from_transaction."""

    def test_simple_expense_with_asset(self, mock_account, mock_entry, mock_metadata):
        """Simple expense: Debit Expense / Credit Asset."""
        asset = mock_account(AccountType.ASSET, "Checking")
        expense = mock_account(AccountType.EXPENSE, "Groceries")

        asset_entry = mock_entry(asset, is_debit=False, amount=Decimal("50.00"))
        expense_entry = mock_entry(expense, is_debit=True, amount=Decimal("50.00"))

        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "REWE purchase"
        txn.counterparty = "REWE"
        txn.is_posted = True
        txn.is_internal_transfer = False
        txn.entries = [expense_entry, asset_entry]
        txn.metadata = mock_metadata()

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.amount == Decimal("50.00")
        assert dto.is_income is False  # Credit to asset = expense
        assert dto.counter_account == "Groceries"
        assert dto.debit_account == "Groceries"
        assert dto.credit_account == "Checking"

    def test_credit_card_purchase(self, mock_account, mock_entry, mock_metadata):
        """Credit card purchase: Debit Expense / Credit Liability."""
        liability = mock_account(AccountType.LIABILITY, "Credit Card")
        expense = mock_account(AccountType.EXPENSE, "Restaurant")

        liability_entry = mock_entry(liability, is_debit=False, amount=Decimal("30.00"))
        expense_entry = mock_entry(expense, is_debit=True, amount=Decimal("30.00"))

        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "Dinner at restaurant"
        txn.counterparty = "Restaurant XYZ"
        txn.is_posted = True
        txn.is_internal_transfer = False
        txn.entries = [expense_entry, liability_entry]
        txn.metadata = mock_metadata()

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.amount == Decimal("30.00")
        assert dto.is_income is False  # Credit to liability = spending
        assert dto.counter_account == "Restaurant"
        assert dto.debit_account == "Restaurant"
        assert dto.credit_account == "Credit Card"

    def test_income_transaction(self, mock_account, mock_entry, mock_metadata):
        """Income transaction: Debit Asset / Credit Income."""
        asset = mock_account(AccountType.ASSET, "Checking")
        income = mock_account(AccountType.INCOME, "Salary")

        asset_entry = mock_entry(asset, is_debit=True, amount=Decimal("3000.00"))
        income_entry = mock_entry(income, is_debit=False, amount=Decimal("3000.00"))

        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "Monthly salary"
        txn.counterparty = "Employer Inc"
        txn.is_posted = True
        txn.is_internal_transfer = False
        txn.entries = [asset_entry, income_entry]
        txn.metadata = mock_metadata()

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.amount == Decimal("3000.00")
        assert dto.is_income is True  # Debit to asset = income
        assert dto.counter_account == "Salary"

    def test_split_transaction_shows_split(
        self, mock_account, mock_entry, mock_metadata
    ):
        """Split transaction shows 'Split' for multiple debits."""
        asset = mock_account(AccountType.ASSET, "Checking")
        expense1 = mock_account(AccountType.EXPENSE, "Groceries")
        expense2 = mock_account(AccountType.EXPENSE, "Household")

        asset_entry = mock_entry(asset, is_debit=False, amount=Decimal("100.00"))
        expense1_entry = mock_entry(expense1, is_debit=True, amount=Decimal("70.00"))
        expense2_entry = mock_entry(expense2, is_debit=True, amount=Decimal("30.00"))

        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "Store purchase"
        txn.counterparty = "Store"
        txn.is_posted = True
        txn.is_internal_transfer = False
        txn.entries = [expense1_entry, expense2_entry, asset_entry]
        txn.metadata = mock_metadata()

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.debit_account == "Split"  # Multiple debit entries
        assert dto.credit_account == "Checking"  # Single credit entry
        assert dto.counter_account == "Split"  # Multiple counter accounts

    def test_internal_transfer_between_assets(
        self,
        mock_account,
        mock_entry,
        mock_metadata,
    ):
        """Internal transfer: Debit Asset1 / Credit Asset2."""
        checking = mock_account(
            AccountType.ASSET,
            "Checking",
            iban="DE89370400440532013000",
        )
        savings = mock_account(
            AccountType.ASSET,
            "Savings",
            iban="DE12345678901234567890",
        )

        checking_entry = mock_entry(checking, is_debit=True, amount=Decimal("500.00"))
        savings_entry = mock_entry(savings, is_debit=False, amount=Decimal("500.00"))

        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "Transfer to savings"
        txn.counterparty = None
        txn.is_posted = True
        txn.is_internal_transfer = True
        txn.entries = [checking_entry, savings_entry]
        # Source IBAN identifies the main account
        txn.metadata = mock_metadata(source_iban="DE89370400440532013000")

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.amount == Decimal("500.00")
        assert dto.is_income is True  # Debit to checking = money in from perspective
        assert dto.counter_account == "Savings"
        assert dto.is_internal_transfer is True

    def test_empty_transaction(self, mock_metadata):
        """Empty transaction returns default values."""
        txn = MagicMock()
        txn.id = uuid4()
        txn.date = MagicMock()
        txn.description = "Empty"
        txn.counterparty = None
        txn.is_posted = False
        txn.is_internal_transfer = False
        txn.entries = []
        txn.metadata = mock_metadata()

        dto = TransactionListItemDTO.from_transaction(txn)

        assert dto.amount == Decimal("0")
        assert dto.currency == "EUR"
        assert dto.is_income is True  # Default
        assert dto.counter_account is None
