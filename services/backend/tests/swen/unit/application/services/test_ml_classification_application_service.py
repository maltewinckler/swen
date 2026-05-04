"""Tests for MLClassificationApplicationService."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from swen.application.services.ml_batch_classification_service import (
    BatchClassificationResult,
)
from swen.application.services.ml_classification_application_service import (
    MLClassificationApplicationService,
    get_counter_account,
    has_fallback_counter_account,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource
from swen.domain.accounting.well_known_accounts import WellKnownAccounts


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


def make_ml_result(account: Account) -> BatchClassificationResult:
    return BatchClassificationResult(
        transaction_id=uuid4(),
        counter_account_id=account.id,
        counter_account_number=account.account_number,
        confidence=0.91,
        tier="hybrid",
        merchant="REWE",
        is_recurring=True,
        recurring_pattern="monthly",
    )


@pytest.mark.asyncio
async def test_resolve_classification_returns_valid_account_for_outflow(
    groceries_account,
):
    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = groceries_account

    account = await MLClassificationApplicationService.resolve_classification(
        ml_result=make_ml_result(groceries_account),
        is_money_outflow=True,
        account_repo=account_repo,
    )

    assert account is groceries_account
    account_repo.find_by_id.assert_awaited_once_with(groceries_account.id)


@pytest.mark.asyncio
async def test_resolve_classification_rejects_direction_mismatch(salary_account):
    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = salary_account

    account = await MLClassificationApplicationService.resolve_classification(
        ml_result=make_ml_result(salary_account),
        is_money_outflow=True,
        account_repo=account_repo,
    )

    assert account is None


@pytest.mark.asyncio
async def test_apply_to_transaction_replaces_counter_account_for_outflow(
    bank_outflow_transaction,
    checking_account,
    fallback_expense_account,
    groceries_account,
):
    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = groceries_account

    result = await MLClassificationApplicationService.apply_to_transaction(
        txn=bank_outflow_transaction,
        ml_result=make_ml_result(groceries_account),
        account_repo=account_repo,
    )

    assert result is not None
    assert result.account is groceries_account
    assert result.old_account is fallback_expense_account
    assert result.changed is True
    assert bank_outflow_transaction.merchant == "REWE"
    assert bank_outflow_transaction.is_recurring is True
    assert bank_outflow_transaction.recurring_pattern == "monthly"

    asset_entry = next(
        entry
        for entry in bank_outflow_transaction.entries
        if entry.account.id == checking_account.id
    )
    counter_entry = next(
        entry
        for entry in bank_outflow_transaction.entries
        if not bank_outflow_transaction.is_entry_protected(entry)
    )

    assert len(bank_outflow_transaction.entries) == 2
    assert asset_entry.is_debit() is False
    assert counter_entry.account is groceries_account
    assert counter_entry.is_debit() is True
    assert get_counter_account(bank_outflow_transaction) is groceries_account


@pytest.mark.asyncio
async def test_apply_to_transaction_uses_credit_counter_for_inflow(
    bank_inflow_transaction,
    checking_account,
    fallback_income_account,
    salary_account,
):
    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = salary_account

    result = await MLClassificationApplicationService.apply_to_transaction(
        txn=bank_inflow_transaction,
        ml_result=make_ml_result(salary_account),
        account_repo=account_repo,
    )

    assert result is not None
    assert result.account is salary_account
    assert result.old_account is fallback_income_account

    asset_entry = next(
        entry
        for entry in bank_inflow_transaction.entries
        if entry.account.id == checking_account.id
    )
    counter_entry = next(
        entry
        for entry in bank_inflow_transaction.entries
        if not bank_inflow_transaction.is_entry_protected(entry)
    )

    assert asset_entry.is_debit() is True
    assert counter_entry.account is salary_account
    assert counter_entry.is_debit() is False


@pytest.mark.asyncio
async def test_apply_to_transaction_returns_none_when_account_is_unchanged(
    user_id,
    checking_account,
    groceries_account,
    amount,
):
    txn = Transaction(
        description="Already categorized",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(groceries_account, amount)
    txn.add_credit(checking_account, amount)

    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = groceries_account

    result = await MLClassificationApplicationService.apply_to_transaction(
        txn=txn,
        ml_result=make_ml_result(groceries_account),
        account_repo=account_repo,
    )

    assert result is None
    assert txn.merchant is None
    assert get_counter_account(txn) is groceries_account


@pytest.mark.asyncio
async def test_apply_to_transaction_rejects_wrong_direction_without_mutation(
    bank_outflow_transaction,
    fallback_expense_account,
    salary_account,
):
    account_repo = AsyncMock()
    account_repo.find_by_id.return_value = salary_account

    result = await MLClassificationApplicationService.apply_to_transaction(
        txn=bank_outflow_transaction,
        ml_result=make_ml_result(salary_account),
        account_repo=account_repo,
    )

    assert result is None
    assert bank_outflow_transaction.merchant is None
    assert get_counter_account(bank_outflow_transaction) is fallback_expense_account


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
