"""Unit tests for ReclassifyDraftsCommand's draft-to-bank-transaction adapter."""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.application.accounting.commands.reclassify_drafts_command import (
    _DraftAsBankTransaction,
    _DraftAsStoredTransaction,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def checking_account(user_id):
    return Account(
        name="Checking",
        account_type=AccountType.ASSET,
        account_number="1000",
        user_id=user_id,
    )


@pytest.fixture
def expense_account(user_id):
    return Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="6000",
        user_id=user_id,
    )


@pytest.fixture
def income_account(user_id):
    return Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="4000",
        user_id=user_id,
    )


def test_draft_as_bank_transaction_is_debit_for_outflow(
    user_id,
    checking_account,
    expense_account,
):
    """Money leaving the account (asset entry credited) must report is_debit()=True.

    Regression test: _DraftAsBankTransaction previously had no is_debit()
    method at all, so reclassifying any non-internal-transfer draft raised
    AttributeError deep inside CounterAccountBatchService.resolve_batch(),
    aborting the whole SSE stream.
    """
    amount = Money(Decimal("45.99"), Currency("EUR"))
    txn = Transaction(
        description="REWE Supermarket",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(expense_account, amount)
    txn.add_credit(checking_account, amount)

    adapted = _DraftAsBankTransaction(txn)

    assert adapted.is_debit() is True
    assert adapted.amount == Decimal("-45.99")


def test_draft_as_bank_transaction_is_debit_for_inflow(
    user_id,
    checking_account,
    income_account,
):
    """Money entering the account (asset entry debited) must report is_debit()=False."""
    amount = Money(Decimal("3000.00"), Currency("EUR"))
    txn = Transaction(
        description="Salary",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(checking_account, amount)
    txn.add_credit(income_account, amount)

    adapted = _DraftAsBankTransaction(txn)

    assert adapted.is_debit() is False
    assert adapted.amount == Decimal("3000.00")


def test_draft_as_stored_transaction_wraps_id_and_transaction(
    user_id,
    checking_account,
    expense_account,
):
    amount = Money(Decimal("10.00"), Currency("EUR"))
    txn = Transaction(
        description="Coffee",
        user_id=user_id,
        source=TransactionSource.BANK_IMPORT,
    )
    txn.add_debit(expense_account, amount)
    txn.add_credit(checking_account, amount)

    wrapped = _DraftAsStoredTransaction(txn)

    assert wrapped.id == txn.id
    assert wrapped.transaction.is_debit() is True
