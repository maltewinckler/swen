"""Tests for SqlAlchemyAnalyticsReadAdapter (analytics read port adapter)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from swen.infrastructure.persistence.sqlalchemy.adapters.analytics import (
    SqlAlchemyAnalyticsReadAdapter,
)
from swen.infrastructure.persistence.sqlalchemy.models.accounting.account_model import (
    AccountModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.accounting.journal_entry_model import (
    JournalEntryModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.accounting.transaction_model import (
    TransactionModel,
)


def _mk_account(*, user_id, name: str, account_type: str) -> AccountModel:
    return AccountModel(
        id=uuid4(),
        user_id=user_id,
        name=name,
        account_type=account_type,
        account_number=None,
        iban=None,
        description=None,
        default_currency="EUR",
        is_active=True,
        parent_id=None,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _mk_tx(*, user_id, dt: datetime, posted: bool = True) -> TransactionModel:
    return TransactionModel(
        id=uuid4(),
        user_id=user_id,
        description="Test",
        date=dt,
        counterparty=None,
        counterparty_iban=None,
        source="manual",
        source_iban=None,
        is_internal_transfer=False,
        transaction_metadata={},
        is_posted=posted,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _mk_entry(*, tx_id, account_id, debit: Decimal) -> JournalEntryModel:
    return JournalEntryModel(
        id=uuid4(),
        transaction_id=tx_id,
        account_id=account_id,
        debit_amount=debit,
        credit_amount=Decimal("0.00"),
        currency="EUR",
    )


def _mk_entry_income_credit(*, tx_id, account_id, credit: Decimal) -> JournalEntryModel:
    return JournalEntryModel(
        id=uuid4(),
        transaction_id=tx_id,
        account_id=account_id,
        debit_amount=Decimal("0.00"),
        credit_amount=credit,
        currency="EUR",
    )


def _mk_entry_credit(*, tx_id, account_id, credit: Decimal) -> JournalEntryModel:
    return JournalEntryModel(
        id=uuid4(),
        transaction_id=tx_id,
        account_id=account_id,
        debit_amount=Decimal("0.00"),
        credit_amount=credit,
        currency="EUR",
    )


@pytest.mark.asyncio
async def test_spending_over_time_aggregates_by_month(async_session, user_context):
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    rent = _mk_account(
        user_id=user_context.user_id,
        name="Rent",
        account_type="expense",
    )
    async_session.add_all([groceries, rent])

    nov = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 15, tzinfo=timezone.utc),
        posted=True,
    )
    dec1 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    dec2 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 15, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([nov, dec1, dec2])

    async_session.add_all(
        [
            _mk_entry(tx_id=nov.id, account_id=groceries.id, debit=Decimal("100.00")),
            _mk_entry(tx_id=dec1.id, account_id=groceries.id, debit=Decimal("150.00")),
            _mk_entry(tx_id=dec2.id, account_id=rent.id, debit=Decimal("1000.00")),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    result = await adapter.spending_over_time(months=2, end_month="2024-12")

    assert [dp.period for dp in result.data_points] == ["2024-11", "2024-12"]
    nov_dp = result.data_points[0]
    dec_dp = result.data_points[1]

    assert nov_dp.categories["Groceries"] == Decimal("100.00")
    assert nov_dp.total == Decimal("100.00")
    assert dec_dp.categories["Groceries"] == Decimal("150.00")
    assert dec_dp.categories["Rent"] == Decimal("1000.00")
    assert dec_dp.total == Decimal("1150.00")

    # Sorted by total spending desc
    assert result.categories[0] == "Rent"
    assert result.categories[1] == "Groceries"


@pytest.mark.asyncio
async def test_spending_over_time_excludes_drafts_by_default(
    async_session, user_context
):
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    async_session.add(groceries)

    posted = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    draft = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 2, tzinfo=timezone.utc),
        posted=False,
    )
    async_session.add_all([posted, draft])

    async_session.add_all(
        [
            _mk_entry(
                tx_id=posted.id, account_id=groceries.id, debit=Decimal("100.00")
            ),
            _mk_entry(tx_id=draft.id, account_id=groceries.id, debit=Decimal("50.00")),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.spending_over_time(
        months=1, end_month="2024-12", include_drafts=False
    )

    assert res.data_points[0].categories["Groceries"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_spending_breakdown_calculates_percentages(async_session, user_context):
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    rent = _mk_account(
        user_id=user_context.user_id,
        name="Rent",
        account_type="expense",
    )
    async_session.add_all([groceries, rent])

    tx1 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx2 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx1, tx2])

    async_session.add_all(
        [
            _mk_entry(tx_id=tx1.id, account_id=groceries.id, debit=Decimal("200.00")),
            _mk_entry(tx_id=tx2.id, account_id=rent.id, debit=Decimal("800.00")),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.spending_breakdown(month="2024-12")

    assert res.total == Decimal("1000.00")
    rent_item = next(i for i in res.items if i.category == "Rent")
    groceries_item = next(i for i in res.items if i.category == "Groceries")

    assert rent_item.percentage == Decimal("80.0")
    assert groceries_item.percentage == Decimal("20.0")


@pytest.mark.asyncio
async def test_top_expenses_ranks_and_calculates_fields(async_session, user_context):
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    rent = _mk_account(
        user_id=user_context.user_id,
        name="Rent",
        account_type="expense",
    )
    utilities = _mk_account(
        user_id=user_context.user_id,
        name="Utilities",
        account_type="expense",
    )
    async_session.add_all([groceries, rent, utilities])

    tx1 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx2 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx3 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx1, tx2, tx3])

    async_session.add_all(
        [
            _mk_entry(tx_id=tx1.id, account_id=groceries.id, debit=Decimal("300.00")),
            _mk_entry(tx_id=tx2.id, account_id=rent.id, debit=Decimal("1000.00")),
            _mk_entry(tx_id=tx3.id, account_id=utilities.id, debit=Decimal("150.00")),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.top_expenses(months=1, end_month="2024-12", top_n=2)

    assert res.months_analyzed == 1
    assert res.total_spending == Decimal("1450.00")
    assert len(res.items) == 2
    assert res.items[0].rank == 1
    assert res.items[0].category == "Rent"
    assert res.items[0].total_amount == Decimal("1000.00")
    assert res.items[0].monthly_average == Decimal("1000.00")
    assert res.items[0].percentage_of_total == Decimal("69.0")  # 1000/1450*100=68.97
    assert res.items[0].transaction_count == 1


@pytest.mark.asyncio
async def test_month_comparison_compares_income_and_spending(
    async_session, user_context
):
    salary = _mk_account(
        user_id=user_context.user_id,
        name="Salary",
        account_type="income",
    )
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    async_session.add_all([salary, groceries])

    nov_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 15, tzinfo=timezone.utc),
        posted=True,
    )
    nov_spend = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 20, tzinfo=timezone.utc),
        posted=True,
    )
    dec_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 15, tzinfo=timezone.utc),
        posted=True,
    )
    dec_spend = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 20, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([nov_income, nov_spend, dec_income, dec_spend])

    async_session.add_all(
        [
            _mk_entry_income_credit(
                tx_id=nov_income.id, account_id=salary.id, credit=Decimal("3000.00")
            ),
            _mk_entry(
                tx_id=nov_spend.id, account_id=groceries.id, debit=Decimal("2000.00")
            ),
            _mk_entry_income_credit(
                tx_id=dec_income.id, account_id=salary.id, credit=Decimal("3500.00")
            ),
            _mk_entry(
                tx_id=dec_spend.id, account_id=groceries.id, debit=Decimal("2500.00")
            ),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.month_comparison(month="2024-12")

    assert res.current_month == "December 2024"
    assert res.previous_month == "November 2024"
    assert res.current_income == Decimal("3500.00")
    assert res.previous_income == Decimal("3000.00")
    assert res.income_change == Decimal("500.00")
    assert res.income_change_percentage == Decimal("16.7")

    assert res.current_spending == Decimal("2500.00")
    assert res.previous_spending == Decimal("2000.00")
    assert res.spending_change == Decimal("500.00")
    assert res.spending_change_percentage == Decimal("25.0")

    assert res.current_net == Decimal("1000.00")
    assert res.previous_net == Decimal("1000.00")
    assert res.net_change == Decimal("0.00")
    assert res.net_change_percentage == Decimal("0")

    # Category comparison exists for groceries
    assert len(res.category_comparisons) == 1
    comp = res.category_comparisons[0]
    assert comp.category == "Groceries"
    assert comp.current_amount == Decimal("2500.00")
    assert comp.previous_amount == Decimal("2000.00")
    assert comp.change_amount == Decimal("500.00")
    assert comp.change_percentage == Decimal("25.0")


@pytest.mark.asyncio
async def test_income_over_time_aggregates_by_month_and_min_max(
    async_session,
    user_context,
):
    salary = _mk_account(
        user_id=user_context.user_id,
        name="Salary",
        account_type="income",
    )
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    async_session.add_all([salary, groceries])

    nov_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 15, tzinfo=timezone.utc),
        posted=True,
    )
    dec_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    dec_expense = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 2, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([nov_income, dec_income, dec_expense])

    async_session.add_all(
        [
            _mk_entry_income_credit(
                tx_id=nov_income.id,
                account_id=salary.id,
                credit=Decimal("3000.00"),
            ),
            _mk_entry_income_credit(
                tx_id=dec_income.id,
                account_id=salary.id,
                credit=Decimal("3500.00"),
            ),
            _mk_entry(
                tx_id=dec_expense.id,
                account_id=groceries.id,
                debit=Decimal("100.00"),
            ),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.income_over_time(months=2, end_month="2024-12")

    assert [dp.period for dp in res.data_points] == ["2024-11", "2024-12"]
    assert res.total == Decimal("6500.00")
    assert res.average == Decimal("3250.00")
    assert res.min_value == Decimal("3000.00")
    assert res.max_value == Decimal("3500.00")


@pytest.mark.asyncio
async def test_income_breakdown_aggregates_by_source_and_percentages(
    async_session,
    user_context,
):
    salary = _mk_account(
        user_id=user_context.user_id,
        name="Salary",
        account_type="income",
    )
    dividends = _mk_account(
        user_id=user_context.user_id,
        name="Dividends",
        account_type="income",
    )
    async_session.add_all([salary, dividends])

    tx1 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx2 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 15, tzinfo=timezone.utc),
        posted=True,
    )
    tx3 = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 20, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx1, tx2, tx3])

    async_session.add_all(
        [
            _mk_entry_income_credit(
                tx_id=tx1.id, account_id=salary.id, credit=Decimal("3000.00")
            ),
            _mk_entry_income_credit(
                tx_id=tx2.id, account_id=salary.id, credit=Decimal("500.00")
            ),
            _mk_entry_income_credit(
                tx_id=tx3.id, account_id=dividends.id, credit=Decimal("100.00")
            ),
        ],
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.income_breakdown(month="2024-12")

    assert res.total == Decimal("3600.00")
    assert len(res.items) == 2
    assert res.items[0].category == "Salary"
    assert res.items[0].amount == Decimal("3500.00")
    assert res.items[1].category == "Dividends"
    assert res.items[1].amount == Decimal("100.00")
    assert res.items[0].percentage == Decimal("97.2")  # 3500/3600*100=97.22
    assert res.items[1].percentage == Decimal("2.8")


@pytest.mark.asyncio
async def test_net_income_over_time_calculates_income_minus_expenses(
    async_session,
    user_context,
):
    salary = _mk_account(user_id=user_context.user_id, name="Salary", account_type="income")
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    async_session.add_all([salary, groceries])

    dec_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 15, tzinfo=timezone.utc),
        posted=True,
    )
    dec_spend = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 20, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([dec_income, dec_spend])

    async_session.add_all(
        [
            _mk_entry_income_credit(
                tx_id=dec_income.id, account_id=salary.id, credit=Decimal("3000.00")
            ),
            _mk_entry(
                tx_id=dec_spend.id, account_id=groceries.id, debit=Decimal("2000.00")
            ),
        ]
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.net_income_over_time(months=1, end_month="2024-12")

    assert res.data_points[0].period == "2024-12"
    assert res.data_points[0].value == Decimal("1000.00")


@pytest.mark.asyncio
async def test_savings_rate_over_time_calculates_rate_and_average(
    async_session,
    user_context,
):
    salary = _mk_account(user_id=user_context.user_id, name="Salary", account_type="income")
    groceries = _mk_account(user_id=user_context.user_id, name="Groceries", account_type="expense")
    async_session.add_all([salary, groceries])

    nov_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 15, tzinfo=timezone.utc),
        posted=True,
    )
    nov_spend = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 11, 20, tzinfo=timezone.utc),
        posted=True,
    )
    dec_income = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 15, tzinfo=timezone.utc),
        posted=True,
    )
    dec_spend = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 20, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([nov_income, nov_spend, dec_income, dec_spend])

    async_session.add_all(
        [
            _mk_entry_income_credit(
                tx_id=nov_income.id, account_id=salary.id, credit=Decimal("2000.00")
            ),
            _mk_entry(
                tx_id=nov_spend.id, account_id=groceries.id, debit=Decimal("1000.00")
            ),  # 50.0%
            _mk_entry_income_credit(
                tx_id=dec_income.id, account_id=salary.id, credit=Decimal("2000.00")
            ),
            _mk_entry(
                tx_id=dec_spend.id, account_id=groceries.id, debit=Decimal("1500.00")
            ),  # 25.0%
        ]
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.savings_rate_over_time(months=2, end_month="2024-12")

    nov = next(dp for dp in res.data_points if dp.period == "2024-11")
    dec = next(dp for dp in res.data_points if dp.period == "2024-12")
    assert res.currency == "%"
    assert nov.value == Decimal("50.0")
    assert dec.value == Decimal("25.0")
    assert res.average == Decimal("37.5")


@pytest.mark.asyncio
async def test_balance_history_over_time_tracks_asset_balances_and_sorting(
    async_session,
    user_context,
):
    checking = _mk_account(
        user_id=user_context.user_id,
        name="Checking Account",
        account_type="asset",
    )
    savings = _mk_account(
        user_id=user_context.user_id,
        name="Savings Account",
        account_type="asset",
    )
    groceries = _mk_account(
        user_id=user_context.user_id,
        name="Groceries",
        account_type="expense",
    )
    async_session.add_all([checking, savings, groceries])

    tx_checking = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx_savings = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 2, tzinfo=timezone.utc),
        posted=True,
    )
    tx_expense = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 3, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx_checking, tx_savings, tx_expense])

    async_session.add_all(
        [
            _mk_entry(tx_id=tx_checking.id, account_id=checking.id, debit=Decimal("5000.00")),
            _mk_entry(tx_id=tx_savings.id, account_id=savings.id, debit=Decimal("10000.00")),
            _mk_entry(tx_id=tx_expense.id, account_id=groceries.id, debit=Decimal("123.00")),
        ]
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.balance_history_over_time(months=1, end_month="2024-12")

    assert res.categories == ["Savings Account", "Checking Account"]
    assert res.data_points[0].categories["Checking Account"] == Decimal("5000.00")
    assert res.data_points[0].categories["Savings Account"] == Decimal("10000.00")
    assert res.data_points[0].total == Decimal("15000.00")


@pytest.mark.asyncio
async def test_net_worth_over_time_assets_minus_liabilities(
    async_session,
    user_context,
):
    checking = _mk_account(
        user_id=user_context.user_id,
        name="Checking Account",
        account_type="asset",
    )
    savings = _mk_account(
        user_id=user_context.user_id,
        name="Savings Account",
        account_type="asset",
    )
    cc = _mk_account(
        user_id=user_context.user_id,
        name="Credit Card",
        account_type="liability",
    )
    async_session.add_all([checking, savings, cc])

    tx_assets = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    tx_liab = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 2, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx_assets, tx_liab])

    async_session.add_all(
        [
            _mk_entry(tx_id=tx_assets.id, account_id=checking.id, debit=Decimal("10000.00")),
            _mk_entry(tx_id=tx_assets.id, account_id=savings.id, debit=Decimal("10000.00")),
            _mk_entry_credit(tx_id=tx_liab.id, account_id=cc.id, credit=Decimal("2000.00")),
        ]
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.net_worth_over_time(months=1, end_month="2024-12")

    assert res.data_points[0].value == Decimal("18000.00")
    assert res.total == Decimal("18000.00")


@pytest.mark.asyncio
async def test_net_worth_over_time_handles_negative_liability_overpayment(
    async_session,
    user_context,
):
    """Test that overpayment on a liability (negative balance) increases net worth.

    When you overpay a credit card, the liability balance becomes negative,
    which means the credit card company owes YOU money. This should increase
    your net worth, not decrease it.
    """
    checking = _mk_account(
        user_id=user_context.user_id,
        name="Checking Account",
        account_type="asset",
    )
    cc = _mk_account(
        user_id=user_context.user_id,
        name="Credit Card",
        account_type="liability",
    )
    async_session.add_all([checking, cc])

    # Initial asset deposit
    tx_deposit = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 1, tzinfo=timezone.utc),
        posted=True,
    )
    # Credit card purchase: increases liability
    tx_purchase = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 2, tzinfo=timezone.utc),
        posted=True,
    )
    # Overpayment: pay more than owed, making liability negative
    tx_overpay = _mk_tx(
        user_id=user_context.user_id,
        dt=datetime(2024, 12, 3, tzinfo=timezone.utc),
        posted=True,
    )
    async_session.add_all([tx_deposit, tx_purchase, tx_overpay])

    async_session.add_all(
        [
            # Deposit 10000 to checking
            _mk_entry(
                tx_id=tx_deposit.id, account_id=checking.id, debit=Decimal("10000.00")
            ),
            # Credit card purchase of 500 (credit to liability = increase debt)
            _mk_entry_credit(
                tx_id=tx_purchase.id, account_id=cc.id, credit=Decimal("500.00")
            ),
            # Overpay credit card by 700 (debit to liability = decrease debt)
            # This makes the liability balance -200 (they owe us 200)
            _mk_entry(tx_id=tx_overpay.id, account_id=cc.id, debit=Decimal("700.00")),
        ]
    )
    await async_session.flush()

    adapter = SqlAlchemyAnalyticsReadAdapter(async_session, user_context)
    res = await adapter.net_worth_over_time(months=1, end_month="2024-12")

    # Assets: 10000
    # Liabilities: 500 - 700 = -200 (negative = credit balance / overpayment)
    # Net worth = 10000 - (-200) = 10200
    # The overpayment should ADD to net worth, not subtract
    assert res.data_points[0].value == Decimal("10200.00")
    assert res.total == Decimal("10200.00")
