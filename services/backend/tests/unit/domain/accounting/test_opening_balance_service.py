"""Unit tests for OpeningBalanceService."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import InvalidAccountTypeError
from swen.domain.accounting.services import (
    OPENING_BALANCE_IBAN_KEY,
    OPENING_BALANCE_METADATA_KEY,
    OpeningBalanceService,
)
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankTransaction

# Test user ID for all opening balance tests
TEST_USER_ID = uuid4()


class TestCalculateOpeningBalance:
    """Tests for calculate_opening_balance method."""

    @pytest.fixture
    def service(self) -> OpeningBalanceService:
        """Create service instance."""
        return OpeningBalanceService()

    @pytest.fixture
    def sample_transactions(self) -> list[BankTransaction]:
        """Create sample bank transactions for testing."""
        return [
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("500.00"),  # Income
                currency="EUR",
                purpose="Salary",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 20),
                value_date=date(2025, 1, 20),
                amount=Decimal("-100.00"),  # Expense
                currency="EUR",
                purpose="Groceries",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 25),
                value_date=date(2025, 1, 25),
                amount=Decimal("-200.00"),  # Expense
                currency="EUR",
                purpose="Rent",
            ),
        ]

    def test_calculate_positive_opening_balance(
        self,
        service: OpeningBalanceService,
        sample_transactions: list[BankTransaction],
    ):
        """Should calculate opening balance when current > net change."""
        # Current balance is 1000
        # Net change = +500 - 100 - 200 = +200
        # Opening balance = 1000 - 200 = 800
        current_balance = Decimal("1000.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=sample_transactions,
        )

        assert result == Decimal("800.00")

    def test_calculate_negative_opening_balance(
        self,
        service: OpeningBalanceService,
        sample_transactions: list[BankTransaction],
    ):
        """Should handle negative opening balance (overdraft scenario)."""
        # Current balance is 100 (was in overdraft before)
        # Net change = +500 - 100 - 200 = +200
        # Opening balance = 100 - 200 = -100 (was in overdraft)
        current_balance = Decimal("100.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=sample_transactions,
        )

        assert result == Decimal("-100.00")

    def test_calculate_zero_opening_balance(
        self,
        service: OpeningBalanceService,
        sample_transactions: list[BankTransaction],
    ):
        """Should handle zero opening balance."""
        # Net change = +200, current = 200
        # Opening balance = 200 - 200 = 0
        current_balance = Decimal("200.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=sample_transactions,
        )

        assert result == Decimal("0.00")

    def test_calculate_with_empty_transactions(self, service: OpeningBalanceService):
        """Should return current balance when no transactions."""
        current_balance = Decimal("1000.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=[],
        )

        assert result == Decimal("1000.00")

    def test_calculate_with_only_expenses(self, service: OpeningBalanceService):
        """Should correctly calculate when only expenses."""
        transactions = [
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("-100.00"),
                currency="EUR",
                purpose="Expense 1",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 20),
                value_date=date(2025, 1, 20),
                amount=Decimal("-50.00"),
                currency="EUR",
                purpose="Expense 2",
            ),
        ]
        # Current balance = 100, net change = -150
        # Opening balance = 100 - (-150) = 250
        current_balance = Decimal("100.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=transactions,
        )

        assert result == Decimal("250.00")

    def test_calculate_with_only_income(self, service: OpeningBalanceService):
        """Should correctly calculate when only income."""
        transactions = [
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("500.00"),
                currency="EUR",
                purpose="Income 1",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 20),
                value_date=date(2025, 1, 20),
                amount=Decimal("300.00"),
                currency="EUR",
                purpose="Income 2",
            ),
        ]
        # Current balance = 1000, net change = +800
        # Opening balance = 1000 - 800 = 200
        current_balance = Decimal("1000.00")

        result = service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=transactions,
        )

        assert result == Decimal("200.00")


class TestCreateOpeningBalanceTransaction:
    """Tests for create_opening_balance_transaction method."""

    @pytest.fixture
    def service(self) -> OpeningBalanceService:
        """Create service instance."""
        return OpeningBalanceService()

    @pytest.fixture
    def asset_account(self) -> Account:
        """Create sample asset account."""
        return Account(
            name="DKB Checking",
            account_type=AccountType.ASSET,
            account_number="DE89370400440532013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

    @pytest.fixture
    def equity_account(self) -> Account:
        """Create sample equity account."""
        return Account(
            name="Anfangssaldo (Opening Balance)",
            account_type=AccountType.EQUITY,
            account_number="2000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

    def test_create_positive_balance_transaction(
        self,
        service: OpeningBalanceService,
        asset_account: Account,
        equity_account: Account,
    ):
        """Should create correct entries for positive balance."""
        balance_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        iban = "DE89370400440532013000"

        txn = service.create_opening_balance_transaction(
            asset_account=asset_account,
            opening_balance_account=equity_account,
            amount=Decimal("1000.00"),
            currency="EUR",
            balance_date=balance_date,
            iban=iban,
            user_id=TEST_USER_ID,
        )

        # Check transaction was created
        assert txn is not None

        # Check transaction properties
        assert txn.is_posted is True
        assert "Opening Balance" in txn.description
        assert txn.date == balance_date
        assert txn.user_id == TEST_USER_ID

        # Check metadata
        assert txn.has_metadata_raw(OPENING_BALANCE_METADATA_KEY)
        assert txn.get_metadata_raw(OPENING_BALANCE_METADATA_KEY) is True
        assert txn.get_metadata_raw(OPENING_BALANCE_IBAN_KEY) == iban

        # Check entries - positive balance: Debit Asset, Credit Equity
        entries = txn.entries
        assert len(entries) == 2

        debit_entry = next(e for e in entries if e.is_debit())
        credit_entry = next(e for e in entries if not e.is_debit())

        assert debit_entry.account == asset_account
        assert debit_entry.debit.amount == Decimal("1000.00")

        assert credit_entry.account == equity_account
        assert credit_entry.credit.amount == Decimal("1000.00")

    def test_create_negative_balance_transaction(
        self,
        service: OpeningBalanceService,
        asset_account: Account,
        equity_account: Account,
    ):
        """Should create correct entries for negative balance (overdraft)."""
        balance_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        iban = "DE89370400440532013000"

        txn = service.create_opening_balance_transaction(
            asset_account=asset_account,
            opening_balance_account=equity_account,
            amount=Decimal("-500.00"),  # Overdraft
            currency="EUR",
            balance_date=balance_date,
            iban=iban,
            user_id=TEST_USER_ID,
        )

        # Check transaction was created
        assert txn is not None

        # Check transaction is posted
        assert txn.is_posted is True

        # Check entries - negative balance: Credit Asset, Debit Equity
        entries = txn.entries
        assert len(entries) == 2

        debit_entry = next(e for e in entries if e.is_debit())
        credit_entry = next(e for e in entries if not e.is_debit())

        # For negative balance, equity is debited and asset is credited
        assert debit_entry.account == equity_account
        assert debit_entry.debit.amount == Decimal("500.00")

        assert credit_entry.account == asset_account
        assert credit_entry.credit.amount == Decimal("500.00")

    def test_create_zero_balance_transaction(
        self,
        service: OpeningBalanceService,
        asset_account: Account,
        equity_account: Account,
    ):
        """Should not create a transaction for an exactly zero opening balance."""
        balance_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        iban = "DE89370400440532013000"

        txn = service.create_opening_balance_transaction(
            asset_account=asset_account,
            opening_balance_account=equity_account,
            amount=Decimal("0.00"),
            currency="EUR",
            balance_date=balance_date,
            iban=iban,
            user_id=TEST_USER_ID,
        )

        assert txn is None

    def test_reject_non_asset_account(
        self,
        service: OpeningBalanceService,
        equity_account: Account,
    ):
        """Should reject if asset_account is not ASSET type."""
        expense_account = Account(
            name="Expenses",
            account_type=AccountType.EXPENSE,
            account_number="4000",
            user_id=TEST_USER_ID,
        )
        balance_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(InvalidAccountTypeError):
            service.create_opening_balance_transaction(
                asset_account=expense_account,  # Wrong type
                opening_balance_account=equity_account,
                amount=Decimal("1000.00"),
                currency="EUR",
                balance_date=balance_date,
                iban="DE89370400440532013000",
                user_id=TEST_USER_ID,
            )

    def test_reject_non_equity_account(
        self,
        service: OpeningBalanceService,
        asset_account: Account,
    ):
        """Should reject if opening_balance_account is not EQUITY type."""
        income_account = Account(
            name="Income",
            account_type=AccountType.INCOME,
            account_number="3000",
            user_id=TEST_USER_ID,
        )
        balance_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(InvalidAccountTypeError):
            service.create_opening_balance_transaction(
                asset_account=asset_account,
                opening_balance_account=income_account,  # Wrong type
                amount=Decimal("1000.00"),
                currency="EUR",
                balance_date=balance_date,
                iban="DE89370400440532013000",
                user_id=TEST_USER_ID,
            )

    def test_transaction_is_balanced(
        self,
        service: OpeningBalanceService,
        asset_account: Account,
        equity_account: Account,
    ):
        """Should create a balanced transaction."""
        txn = service.create_opening_balance_transaction(
            asset_account=asset_account,
            opening_balance_account=equity_account,
            amount=Decimal("1234.56"),
            currency="EUR",
            balance_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            iban="DE89370400440532013000",
            user_id=TEST_USER_ID,
        )

        # Check transaction was created
        assert txn is not None

        # Transaction should be balanced (posting validates this)
        assert txn.is_balanced()


class TestGetEarliestTransactionDate:
    """Tests for get_earliest_transaction_date method."""

    @pytest.fixture
    def service(self) -> OpeningBalanceService:
        """Create service instance."""
        return OpeningBalanceService()

    def test_get_earliest_date(self, service: OpeningBalanceService):
        """Should return the earliest booking date."""
        transactions = [
            BankTransaction(
                booking_date=date(2025, 1, 20),
                value_date=date(2025, 1, 20),
                amount=Decimal("100.00"),
                currency="EUR",
                purpose="Later",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 5),  # Earliest
                value_date=date(2025, 1, 5),
                amount=Decimal("100.00"),
                currency="EUR",
                purpose="Earliest",
            ),
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("100.00"),
                currency="EUR",
                purpose="Middle",
            ),
        ]

        result = service.get_earliest_transaction_date(transactions)

        assert result is not None
        assert result.date() == date(2025, 1, 5)
        assert result.tzinfo == timezone.utc

    def test_get_earliest_date_single_transaction(self, service: OpeningBalanceService):
        """Should work with single transaction."""
        transactions = [
            BankTransaction(
                booking_date=date(2025, 3, 15),
                value_date=date(2025, 3, 15),
                amount=Decimal("100.00"),
                currency="EUR",
                purpose="Only one",
            ),
        ]

        result = service.get_earliest_transaction_date(transactions)

        assert result is not None
        assert result.date() == date(2025, 3, 15)

    def test_get_earliest_date_empty_list(self, service: OpeningBalanceService):
        """Should return None for empty list."""
        result = service.get_earliest_transaction_date([])
        assert result is None

    def test_result_is_start_of_day_utc(self, service: OpeningBalanceService):
        """Should return datetime at start of day in UTC."""
        transactions = [
            BankTransaction(
                booking_date=date(2025, 6, 15),
                value_date=date(2025, 6, 15),
                amount=Decimal("100.00"),
                currency="EUR",
                purpose="Test",
            ),
        ]

        result = service.get_earliest_transaction_date(transactions)

        assert result is not None
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc
