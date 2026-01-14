"""Unit tests for transaction API serialization.

These tests ensure that journal entries are correctly serialized to JSON,
particularly that zero amounts are returned as null (not 0 or "0").

This prevents a bug where the frontend would misclassify transactions
because JavaScript treats "0" as truthy.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.presentation.api.routers.transactions import _transaction_to_response

# Fixed UUID for testing
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestJournalEntrySerialization:
    """Tests for journal entry serialization in API responses.

    The key invariant: if an entry is debit-only, credit should be None (not 0).
    And vice versa: if an entry is credit-only, debit should be None (not 0).

    This is critical because the frontend uses truthy checks to determine
    if an entry has a debit or credit, and "0" or 0 could cause bugs.
    """

    @pytest.fixture
    def asset_account(self) -> Account:
        """Create an asset account (e.g., bank account)."""
        return Account(
            name="Checking Account",
            account_type=AccountType.ASSET,
            account_number="DE123",
            default_currency=Currency("EUR"),
            user_id=TEST_USER_ID,
        )

    @pytest.fixture
    def expense_account(self) -> Account:
        """Create an expense account."""
        return Account(
            name="Groceries",
            account_type=AccountType.EXPENSE,
            account_number="5000",
            default_currency=Currency("EUR"),
            user_id=TEST_USER_ID,
        )

    @pytest.fixture
    def income_account(self) -> Account:
        """Create an income account."""
        return Account(
            name="Salary",
            account_type=AccountType.INCOME,
            account_number="4000",
            default_currency=Currency("EUR"),
            user_id=TEST_USER_ID,
        )

    def test_expense_transaction_serializes_correctly(
        self,
        asset_account: Account,
        expense_account: Account,
    ):
        """Expense transaction: asset credited, expense debited.

        For an expense (money going out):
        - Asset account: credit (decrease)
        - Expense account: debit (increase)

        The serialized response should have:
        - Asset entry: debit=None, credit=amount
        - Expense entry: debit=amount, credit=None
        """
        amount = Money(Decimal("50.00"), Currency("EUR"))

        txn = Transaction(
            description="REWE Groceries",
            user_id=TEST_USER_ID,
            date=datetime.now(tz=timezone.utc),
            counterparty="REWE",
        )
        txn.add_entry(asset_account, credit=amount)
        txn.add_entry(expense_account, debit=amount)

        response = _transaction_to_response(txn)

        # Find entries by account type
        asset_entry = next(e for e in response.entries if e.account_type == "asset")
        expense_entry = next(e for e in response.entries if e.account_type == "expense")

        # Asset entry: should have credit only, debit must be None (not 0)
        assert asset_entry.credit == Decimal("50.00")
        assert asset_entry.debit is None, (
            "Debit should be None for credit-only entry, not 0. "
            "This prevents frontend from misclassifying the transaction."
        )

        # Expense entry: should have debit only, credit must be None (not 0)
        assert expense_entry.debit == Decimal("50.00")
        assert expense_entry.credit is None, (
            "Credit should be None for debit-only entry, not 0. "
            "This prevents frontend from misclassifying the transaction."
        )

    def test_income_transaction_serializes_correctly(
        self,
        asset_account: Account,
        income_account: Account,
    ):
        """Income transaction: asset debited, income credited.

        For income (money coming in):
        - Asset account: debit (increase)
        - Income account: credit (increase)

        The serialized response should have:
        - Asset entry: debit=amount, credit=None
        - Income entry: debit=None, credit=amount
        """
        amount = Money(Decimal("3000.00"), Currency("EUR"))

        txn = Transaction(
            description="Monthly Salary",
            user_id=TEST_USER_ID,
            date=datetime.now(tz=timezone.utc),
            counterparty="Employer",
        )
        txn.add_entry(asset_account, debit=amount)
        txn.add_entry(income_account, credit=amount)

        response = _transaction_to_response(txn)

        # Find entries by account type
        asset_entry = next(e for e in response.entries if e.account_type == "asset")
        income_entry = next(e for e in response.entries if e.account_type == "income")

        # Asset entry: should have debit only, credit must be None (not 0)
        assert asset_entry.debit == Decimal("3000.00")
        assert asset_entry.credit is None, (
            "Credit should be None for debit-only entry, not 0. "
            "This prevents frontend from misclassifying the transaction."
        )

        # Income entry: should have credit only, debit must be None (not 0)
        assert income_entry.credit == Decimal("3000.00")
        assert income_entry.debit is None, (
            "Debit should be None for credit-only entry, not 0. "
            "This prevents frontend from misclassifying the transaction."
        )

    def test_refund_transaction_serializes_correctly(
        self,
        asset_account: Account,
        expense_account: Account,
    ):
        """Refund transaction: asset debited, expense credited.

        For a refund (reversing a prior expense):
        - Asset account: debit (increase - money coming in)
        - Expense account: credit (decrease - reducing expense)

        This is the specific case that caused the original bug!
        The frontend was showing refunds as expenses because debit was "0"
        instead of null.
        """
        amount = Money(Decimal("40.00"), Currency("EUR"))

        txn = Transaction(
            description="Health Insurance Refund",
            user_id=TEST_USER_ID,
            date=datetime.now(tz=timezone.utc),
            counterparty="Techniker Krankenkasse",
        )
        # Refund: money comes IN to asset, expense is credited (reduced)
        txn.add_entry(asset_account, debit=amount)
        txn.add_entry(expense_account, credit=amount)

        response = _transaction_to_response(txn)

        # Find entries by account type
        asset_entry = next(e for e in response.entries if e.account_type == "asset")
        expense_entry = next(e for e in response.entries if e.account_type == "expense")

        # Asset entry: debit only (money coming in)
        assert asset_entry.debit == Decimal("40.00")
        assert asset_entry.credit is None, (
            "Credit should be None for debit-only entry. "
            "Bug: if this is 0 or '0', frontend will misclassify as expense!"
        )

        # Expense entry: credit only (reducing expense)
        assert expense_entry.credit == Decimal("40.00")
        assert expense_entry.debit is None, (
            "Debit should be None for credit-only entry. "
            "Bug: if this is 0 or '0', frontend's isExpense check breaks!"
        )

    def test_serialized_entries_are_json_safe(
        self,
        asset_account: Account,
        expense_account: Account,
    ):
        """Verify that None values serialize properly to JSON null.

        This ensures the Pydantic model correctly excludes None values
        or serializes them as null (not as 0 or "0").
        """
        amount = Money(Decimal("100.00"), Currency("EUR"))

        txn = Transaction(
            description="Test Transaction",
            user_id=TEST_USER_ID,
            date=datetime.now(tz=timezone.utc),
        )
        txn.add_entry(asset_account, credit=amount)
        txn.add_entry(expense_account, debit=amount)

        response = _transaction_to_response(txn)

        # Convert to JSON-like dict
        response_dict = response.model_dump(mode="json")

        for entry in response_dict["entries"]:
            if entry["debit"] is not None:
                # If debit has a value, credit must be null (not 0)
                assert entry["credit"] is None, (
                    f"Entry with debit={entry['debit']} should have credit=null, "
                    f"got credit={entry['credit']}"
                )
            if entry["credit"] is not None:
                # If credit has a value, debit must be null (not 0)
                assert entry["debit"] is None, (
                    f"Entry with credit={entry['credit']} should have debit=null, "
                    f"got debit={entry['debit']}"
                )

