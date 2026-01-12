"""Shared fixtures for analytics query tests."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money


@pytest.fixture
def mock_account_repo():
    """Create a mock account repository."""
    return AsyncMock()


@pytest.fixture
def mock_transaction_repo():
    """Create a mock transaction repository."""
    return AsyncMock()


@pytest.fixture
def sample_expense_accounts():
    """Create sample expense accounts."""
    accounts = []
    for name, number in [
        ("Groceries", "6001"),
        ("Rent", "6002"),
        ("Utilities", "6003"),
        ("Transportation", "6004"),
    ]:
        account = MagicMock(spec=Account)
        account.id = uuid4()
        account.name = name
        account.account_number = number
        account.account_type = AccountType.EXPENSE
        account.default_currency = Currency(code="EUR")
        account.is_active = True
        accounts.append(account)
    return accounts


@pytest.fixture
def sample_income_accounts():
    """Create sample income accounts."""
    accounts = []
    for name, number in [
        ("Salary", "4001"),
        ("Interest", "4002"),
        ("Dividends", "4003"),
    ]:
        account = MagicMock(spec=Account)
        account.id = uuid4()
        account.name = name
        account.account_number = number
        account.account_type = AccountType.INCOME
        account.default_currency = Currency(code="EUR")
        account.is_active = True
        accounts.append(account)
    return accounts


@pytest.fixture
def sample_asset_accounts():
    """Create sample asset accounts."""
    accounts = []
    for name, number in [
        ("Checking Account", "1001"),
        ("Savings Account", "1002"),
    ]:
        account = MagicMock(spec=Account)
        account.id = uuid4()
        account.name = name
        account.account_number = number
        account.account_type = AccountType.ASSET
        account.default_currency = Currency(code="EUR")
        account.is_active = True
        accounts.append(account)
    return accounts


@pytest.fixture
def sample_liability_accounts():
    """Create sample liability accounts."""
    accounts = []
    for name, number in [
        ("Credit Card", "2001"),
    ]:
        account = MagicMock(spec=Account)
        account.id = uuid4()
        account.name = name
        account.account_number = number
        account.account_type = AccountType.LIABILITY
        account.default_currency = Currency(code="EUR")
        account.is_active = True
        accounts.append(account)
    return accounts


def create_mock_entry(account: Account, debit: Decimal | None, credit: Decimal | None):
    """Create a mock journal entry."""
    entry = MagicMock()
    entry.account = account
    if debit:
        entry.debit = Money(amount=debit, currency=Currency(code="EUR"))
        entry.credit = Money(amount=Decimal("0"), currency=Currency(code="EUR"))
        entry.is_debit = MagicMock(return_value=True)
    else:
        entry.debit = Money(amount=Decimal("0"), currency=Currency(code="EUR"))
        entry.credit = Money(amount=credit, currency=Currency(code="EUR"))
        entry.is_debit = MagicMock(return_value=False)
    return entry


def create_mock_transaction(
    date: datetime,
    entries: list,
    is_posted: bool = True,
):
    """Create a mock transaction."""
    txn = MagicMock()
    txn.id = uuid4()
    txn.date = date
    txn.entries = entries
    txn.is_posted = is_posted
    txn.involves_account = MagicMock(
        side_effect=lambda acc: any(e.account == acc for e in entries)
    )
    return txn

