"""Tests for the FinancialSummaryService domain service."""

from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from swen.domain.accounting.entities import AccountType
from swen.domain.accounting.services import FinancialSummaryService


def _account(account_type: AccountType, name: str) -> Mock:
    account = Mock()
    account.id = uuid4()
    account.name = name
    account.account_type = account_type
    return account


def _entry(account: Mock, *, debit: str = "0", credit: str = "0") -> Mock:
    entry = Mock()
    entry.account = account
    entry.debit = Mock(amount=Decimal(debit))
    entry.credit = Mock(amount=Decimal(credit))
    entry.is_debit.return_value = Decimal(debit) > 0
    return entry


def _txn(*entries: Mock) -> Mock:
    txn = Mock()
    txn.entries = list(entries)
    return txn


class TestPeriodTotals:
    """Double-entry aggregation rules."""

    def test_empty_transactions_return_zero_totals(self):
        totals = FinancialSummaryService.period_totals([])

        assert totals.total_income == Decimal(0)
        assert totals.total_expenses == Decimal(0)
        assert totals.category_spending == {}
        assert totals.net_income == Decimal(0)

    def test_income_accrues_on_the_credit_side(self):
        salary = _account(AccountType.INCOME, "Salary")
        totals = FinancialSummaryService.period_totals(
            [_txn(_entry(salary, credit="3500.00"))],
        )

        assert totals.total_income == Decimal("3500.00")
        assert totals.total_expenses == Decimal(0)

    def test_income_on_the_debit_side_is_ignored(self):
        """A debit to an income account is a reversal, not earnings."""
        salary = _account(AccountType.INCOME, "Salary")
        totals = FinancialSummaryService.period_totals(
            [_txn(_entry(salary, debit="500.00"))],
        )

        assert totals.total_income == Decimal(0)

    def test_expenses_accrue_on_the_debit_side_and_group_by_category(self):
        groceries = _account(AccountType.EXPENSE, "Groceries")
        rent = _account(AccountType.EXPENSE, "Rent")

        totals = FinancialSummaryService.period_totals(
            [
                _txn(_entry(groceries, debit="45.99")),
                _txn(_entry(groceries, debit="12.01")),
                _txn(_entry(rent, debit="950.00")),
            ],
        )

        assert totals.total_expenses == Decimal("1008.00")
        assert totals.category_spending == {
            "Groceries": Decimal("58.00"),
            "Rent": Decimal("950.00"),
        }

    def test_expense_on_the_credit_side_is_ignored(self):
        groceries = _account(AccountType.EXPENSE, "Groceries")
        totals = FinancialSummaryService.period_totals(
            [_txn(_entry(groceries, credit="45.99"))],
        )

        assert totals.total_expenses == Decimal(0)
        assert totals.category_spending == {}

    def test_asset_and_liability_entries_do_not_affect_totals(self):
        checking = _account(AccountType.ASSET, "Checking")
        loan = _account(AccountType.LIABILITY, "Loan")

        totals = FinancialSummaryService.period_totals(
            [_txn(_entry(checking, debit="100.00"), _entry(loan, credit="100.00"))],
        )

        assert totals.total_income == Decimal(0)
        assert totals.total_expenses == Decimal(0)

    def test_net_income_is_income_minus_expenses(self):
        salary = _account(AccountType.INCOME, "Salary")
        rent = _account(AccountType.EXPENSE, "Rent")

        totals = FinancialSummaryService.period_totals(
            [_txn(_entry(salary, credit="3500.00"), _entry(rent, debit="950.00"))],
        )

        assert totals.net_income == Decimal("2550.00")

    def test_totals_are_immutable(self):
        totals = FinancialSummaryService.period_totals([])

        with pytest.raises(ValidationError):
            totals.total_income = Decimal("1")


class TestAssetBalances:
    """Only asset accounts contribute to reported balances."""

    def test_non_asset_accounts_are_excluded(self):
        expense = _account(AccountType.EXPENSE, "Groceries")
        balance_service = Mock()

        balances = FinancialSummaryService.asset_balances(
            accounts=[expense],
            transactions=[],
            balance_service=balance_service,
        )

        assert balances == []
        balance_service.calculate_balance.assert_not_called()

    def test_asset_accounts_are_included_with_their_balance(self):
        checking = _account(AccountType.ASSET, "Checking")
        balance_service = Mock()
        balance_service.calculate_balance.return_value = Mock(
            amount=Decimal("2543.67"),
        )

        balances = FinancialSummaryService.asset_balances(
            accounts=[checking],
            transactions=[],
            balance_service=balance_service,
        )

        assert balances == [(checking, Decimal("2543.67"))]

    def test_only_transactions_touching_the_account_are_passed_through(self):
        checking = _account(AccountType.ASSET, "Checking")
        relevant, unrelated = _txn(), _txn()
        checking_matches = {id(relevant)}
        for txn in (relevant, unrelated):
            txn.involves_account = lambda _account, _t=txn: id(_t) in checking_matches

        balance_service = Mock()
        balance_service.calculate_balance.return_value = Mock(amount=Decimal(0))

        FinancialSummaryService.asset_balances(
            accounts=[checking],
            transactions=[relevant, unrelated],
            balance_service=balance_service,
        )

        passed = balance_service.calculate_balance.call_args.kwargs["transactions"]
        assert passed == [relevant]
