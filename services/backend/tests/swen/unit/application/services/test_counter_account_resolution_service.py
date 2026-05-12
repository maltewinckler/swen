"""Tests for CounterAccountResolutionService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.integration.services.counter_account_resolution_service import (
    CounterAccountResolutionService,
    has_fallback_counter_account,
)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def amount():
    return Money(Decimal("50.00"), Currency("EUR"))


@pytest.fixture
def checking_account(user_id):
    return Account(
        name="Checking",
        account_type=AccountType.ASSET,
        account_number="1000",
        user_id=user_id,
    )


@pytest.fixture
def fallback_expense_account(user_id):
    return Account(
        name="Fallback Expense",
        account_type=AccountType.EXPENSE,
        account_number=WellKnownAccounts.FALLBACK_EXPENSE,
        user_id=user_id,
    )


@pytest.fixture
def fallback_income_account(user_id):
    return Account(
        name="Fallback Income",
        account_type=AccountType.INCOME,
        account_number=WellKnownAccounts.FALLBACK_INCOME,
        user_id=user_id,
    )


@pytest.fixture
def groceries_account(user_id):
    return Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="6000",
        user_id=user_id,
    )


@pytest.fixture
def salary_account(user_id):
    return Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="4000",
        user_id=user_id,
    )


@pytest.fixture
def bank_outflow_transaction(
    user_id,
    checking_account,
    fallback_expense_account,
    amount,
):
    txn = Transaction(
        description="REWE SAGT DANKE",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(fallback_expense_account, amount)
    txn.add_credit(checking_account, amount)
    return txn


@pytest.fixture
def bank_inflow_transaction(
    user_id,
    checking_account,
    fallback_income_account,
    amount,
):
    txn = Transaction(
        description="SALARY PAYMENT",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(checking_account, amount)
    txn.add_credit(fallback_income_account, amount)
    return txn


def test_is_valid_proposal_accepts_expense_for_outflow(groceries_account):
    assert CounterAccountResolutionService.is_valid_proposal(
        is_money_outflow=True,
        account=groceries_account,
    )


def test_is_valid_proposal_rejects_income_for_outflow(salary_account):
    assert not CounterAccountResolutionService.is_valid_proposal(
        is_money_outflow=True,
        account=salary_account,
    )


def test_is_valid_proposal_accepts_income_for_inflow(salary_account):
    assert CounterAccountResolutionService.is_valid_proposal(
        is_money_outflow=False,
        account=salary_account,
    )


def test_is_valid_proposal_rejects_expense_for_inflow(groceries_account):
    assert not CounterAccountResolutionService.is_valid_proposal(
        is_money_outflow=False,
        account=groceries_account,
    )


def test_has_fallback_counter_account_detects_only_fallback_accounts(
    bank_outflow_transaction,
    user_id,
    checking_account,
    groceries_account,
    amount,
):
    non_fallback_txn = Transaction(
        description="Categorized draft",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    non_fallback_txn.add_debit(groceries_account, amount)
    non_fallback_txn.add_credit(checking_account, amount)

    assert has_fallback_counter_account(bank_outflow_transaction) is True
    assert has_fallback_counter_account(non_fallback_txn) is False
