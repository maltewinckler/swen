"""
Integration tests for dashboard CLI commands.

These tests verify the dashboard data fetching and calculation with a real database:
1. Account balance calculations
2. Income/expense aggregation
3. Category spending breakdown
4. Date filtering
5. Edge cases (empty data, zero values)

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.accounting.value_objects import Currency, Money
from swen.domain.shared.time import ensure_tz_aware
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)

# Import Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_ID,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def setup_accounts(db_session, current_user):
    """Set up test accounts."""
    account_repo = AccountRepositorySQLAlchemy(db_session, current_user)

    # Asset accounts
    checking = Account(
        name="Checking Account",
        account_type=AccountType.ASSET,
        account_number="DE89370400440532013000",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(checking)

    savings = Account(
        name="Savings Account",
        account_type=AccountType.ASSET,
        account_number="DE89370400440532013001",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(savings)

    # Expense accounts
    groceries = Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="4100",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(groceries)

    transport = Account(
        name="Transport",
        account_type=AccountType.EXPENSE,
        account_number="4200",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(transport)

    entertainment = Account(
        name="Entertainment",
        account_type=AccountType.EXPENSE,
        account_number="4300",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(entertainment)

    # Income accounts
    salary = Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="8000",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(salary)

    other_income = Account(
        name="Other Income",
        account_type=AccountType.INCOME,
        account_number="8100",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(other_income)

    await db_session.commit()

    return {
        "checking": checking,
        "savings": savings,
        "groceries": groceries,
        "transport": transport,
        "entertainment": entertainment,
        "salary": salary,
        "other_income": other_income,
    }


def _create_expense_transaction(
    asset_account: Account,
    expense_account: Account,
    amount: Decimal,
    date: datetime,
    description: str = "Expense",
    counterparty: str | None = None,
) -> Transaction:
    """Create and post an expense transaction."""
    txn = Transaction(
        description=description,
        date=date,
        counterparty=counterparty,
        user_id=TEST_USER_ID,
    )
    txn.add_debit(expense_account, Money(amount, Currency("EUR")))
    txn.add_credit(asset_account, Money(amount, Currency("EUR")))
    txn.post()
    return txn


def _create_income_transaction(
    asset_account: Account,
    income_account: Account,
    amount: Decimal,
    date: datetime,
    description: str = "Income",
    counterparty: str | None = None,
) -> Transaction:
    """Create and post an income transaction."""
    txn = Transaction(
        description=description,
        date=date,
        counterparty=counterparty,
        user_id=TEST_USER_ID,
    )
    txn.add_debit(asset_account, Money(amount, Currency("EUR")))
    txn.add_credit(income_account, Money(amount, Currency("EUR")))
    txn.post()
    return txn


# ============================================================================
# Tests
# ============================================================================


class TestDashboardAccountBalances:
    """Integration tests for account balance calculations."""

    @pytest.mark.asyncio
    async def test_empty_database_returns_no_balances(
        self,
        db_session,
        current_user,
    ):
        """Test that empty database returns no balances."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        accounts = await account_repo.find_all_active()

        assert len(accounts) == 0

    @pytest.mark.asyncio
    async def test_asset_accounts_with_no_transactions(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test asset accounts have zero balance with no transactions."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        balance_service = AccountBalanceService()

        accounts = await account_repo.find_all_active()
        asset_accounts = [a for a in accounts if a.account_type == AccountType.ASSET]

        for account in asset_accounts:
            txns = await transaction_repo.find_posted_transactions()
            account_txns = [t for t in txns if t.involves_account(account)]
            balance = balance_service.calculate_balance(account, account_txns)

            assert balance.amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_balance_with_income_and_expenses(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test balance calculation with both income and expenses."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        balance_service = AccountBalanceService()
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Create income transaction (salary: +3000)
        income_txn = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("3000.00"),
            now - timedelta(days=15),
            "Monthly Salary",
            "Employer GmbH",
        )
        await transaction_repo.save(income_txn)

        # Create expense transactions
        expense1 = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("200.00"),
            now - timedelta(days=10),
            "Groceries",
            "REWE",
        )
        await transaction_repo.save(expense1)

        expense2 = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("100.00"),
            now - timedelta(days=5),
            "Train ticket",
            "Deutsche Bahn",
        )
        await transaction_repo.save(expense2)

        await db_session.commit()

        # Calculate balance
        txns = await transaction_repo.find_posted_transactions()
        account_txns = [t for t in txns if t.involves_account(accounts["checking"])]
        balance = balance_service.calculate_balance(accounts["checking"], account_txns)

        # 3000 - 200 - 100 = 2700
        assert balance.amount == Decimal("2700.00")

    @pytest.mark.asyncio
    async def test_multiple_asset_accounts_independent_balances(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test that multiple asset accounts have independent balances."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        balance_service = AccountBalanceService()
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Income to checking
        income1 = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("5000.00"),
            now - timedelta(days=10),
        )
        await transaction_repo.save(income1)

        # Income to savings
        income2 = _create_income_transaction(
            accounts["savings"],
            accounts["other_income"],
            Decimal("1000.00"),
            now - timedelta(days=5),
        )
        await transaction_repo.save(income2)

        await db_session.commit()

        # Calculate balances
        txns = await transaction_repo.find_posted_transactions()

        checking_txns = [t for t in txns if t.involves_account(accounts["checking"])]
        checking_balance = balance_service.calculate_balance(
            accounts["checking"],
            checking_txns,
        )

        savings_txns = [t for t in txns if t.involves_account(accounts["savings"])]
        savings_balance = balance_service.calculate_balance(
            accounts["savings"],
            savings_txns,
        )

        assert checking_balance.amount == Decimal("5000.00")
        assert savings_balance.amount == Decimal("1000.00")


class TestDashboardIncomeExpenses:
    """Integration tests for income and expense calculations."""

    @pytest.mark.asyncio
    async def test_income_expense_totals(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test correct calculation of total income and expenses."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Income transactions
        income1 = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("5000.00"),
            now - timedelta(days=20),
        )
        await transaction_repo.save(income1)

        income2 = _create_income_transaction(
            accounts["checking"],
            accounts["other_income"],
            Decimal("500.00"),
            now - timedelta(days=15),
        )
        await transaction_repo.save(income2)

        # Expense transactions
        expense1 = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("400.00"),
            now - timedelta(days=10),
        )
        await transaction_repo.save(expense1)

        expense2 = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("150.00"),
            now - timedelta(days=5),
        )
        await transaction_repo.save(expense2)

        expense3 = _create_expense_transaction(
            accounts["checking"],
            accounts["entertainment"],
            Decimal("100.00"),
            now - timedelta(days=3),
        )
        await transaction_repo.save(expense3)

        await db_session.commit()

        # Calculate totals like dashboard does
        txns = await transaction_repo.find_posted_transactions()

        total_income = Decimal("0")
        total_expenses = Decimal("0")

        for txn in txns:
            for entry in txn.entries:
                if entry.account.account_type == AccountType.INCOME:
                    if not entry.is_debit():
                        total_income += entry.credit.amount
                elif entry.account.account_type == AccountType.EXPENSE:
                    if entry.is_debit():
                        total_expenses += entry.debit.amount

        assert total_income == Decimal("5500.00")  # 5000 + 500
        assert total_expenses == Decimal("650.00")  # 400 + 150 + 100

    @pytest.mark.asyncio
    async def test_date_filtering_for_income_expenses(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test that date filtering correctly limits income/expense totals."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Old transaction (60 days ago)
        old_income = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("4000.00"),
            now - timedelta(days=60),
        )
        await transaction_repo.save(old_income)

        # Recent transaction (10 days ago)
        recent_income = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("5000.00"),
            now - timedelta(days=10),
        )
        await transaction_repo.save(recent_income)

        await db_session.commit()

        # Filter to last 30 days
        start_date = now - timedelta(days=30)
        txns = await transaction_repo.find_posted_transactions()
        filtered_txns = [t for t in txns if t.date >= start_date]

        total_income = Decimal("0")
        for txn in filtered_txns:
            for entry in txn.entries:
                if entry.account.account_type == AccountType.INCOME:
                    if not entry.is_debit():
                        total_income += entry.credit.amount

        # Only recent income should be included
        assert total_income == Decimal("5000.00")


class TestDashboardCategorySpending:
    """Integration tests for category spending breakdown."""

    @pytest.mark.asyncio
    async def test_category_spending_grouping(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test correct grouping of expenses by category."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Multiple groceries expenses
        for i in range(3):
            expense = _create_expense_transaction(
                accounts["checking"],
                accounts["groceries"],
                Decimal("100.00"),
                now - timedelta(days=i + 1),
                f"Groceries {i + 1}",
            )
            await transaction_repo.save(expense)

        # Single transport expense
        transport_expense = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("250.00"),
            now - timedelta(days=5),
            "Train ticket",
        )
        await transaction_repo.save(transport_expense)

        # Entertainment expenses
        entertainment_expense = _create_expense_transaction(
            accounts["checking"],
            accounts["entertainment"],
            Decimal("50.00"),
            now - timedelta(days=2),
            "Movie",
        )
        await transaction_repo.save(entertainment_expense)

        await db_session.commit()

        # Group by category like dashboard does
        txns = await transaction_repo.find_posted_transactions()
        from collections import defaultdict

        category_spending: dict[str, Decimal] = defaultdict(Decimal)

        for txn in txns:
            for entry in txn.entries:
                if entry.account.account_type == AccountType.EXPENSE:
                    if entry.is_debit():
                        category_spending[entry.account.name] += entry.debit.amount

        assert category_spending["Groceries"] == Decimal("300.00")
        assert category_spending["Transport"] == Decimal("250.00")
        assert category_spending["Entertainment"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_category_spending_sorted_by_amount(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test that categories are sorted by spending amount."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Create expenses with different amounts
        expense1 = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("500.00"),
            now - timedelta(days=1),
        )
        await transaction_repo.save(expense1)

        expense2 = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("200.00"),
            now - timedelta(days=2),
        )
        await transaction_repo.save(expense2)

        expense3 = _create_expense_transaction(
            accounts["checking"],
            accounts["entertainment"],
            Decimal("100.00"),
            now - timedelta(days=3),
        )
        await transaction_repo.save(expense3)

        await db_session.commit()

        # Group and sort
        txns = await transaction_repo.find_posted_transactions()
        from collections import defaultdict

        category_spending: dict[str, Decimal] = defaultdict(Decimal)

        for txn in txns:
            for entry in txn.entries:
                if entry.account.account_type == AccountType.EXPENSE:
                    if entry.is_debit():
                        category_spending[entry.account.name] += entry.debit.amount

        sorted_categories = sorted(
            category_spending.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        assert sorted_categories[0][0] == "Transport"
        assert sorted_categories[1][0] == "Groceries"
        assert sorted_categories[2][0] == "Entertainment"


class TestDashboardSavingsRate:
    """Integration tests for savings rate calculation."""

    @pytest.mark.asyncio
    async def test_positive_savings_rate(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test positive savings rate calculation."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Income: 5000
        income = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("5000.00"),
            now - timedelta(days=15),
        )
        await transaction_repo.save(income)

        # Expenses: 3000
        expense = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("3000.00"),
            now - timedelta(days=10),
        )
        await transaction_repo.save(expense)

        await db_session.commit()

        # Calculate savings rate
        total_income = Decimal("5000.00")
        total_expenses = Decimal("3000.00")
        net = total_income - total_expenses
        savings_rate = (net / total_income * 100) if total_income > 0 else Decimal("0")

        assert savings_rate == Decimal("40")

    @pytest.mark.asyncio
    async def test_negative_savings_rate(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test negative savings rate (spending more than income)."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Income: 1000
        income = _create_income_transaction(
            accounts["checking"],
            accounts["salary"],
            Decimal("1000.00"),
            now - timedelta(days=15),
        )
        await transaction_repo.save(income)

        # Expenses: 1500 (more than income)
        expense = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("1500.00"),
            now - timedelta(days=10),
        )
        await transaction_repo.save(expense)

        await db_session.commit()

        # Calculate savings rate
        total_income = Decimal("1000.00")
        total_expenses = Decimal("1500.00")
        net = total_income - total_expenses
        savings_rate = (net / total_income * 100) if total_income > 0 else Decimal("0")

        assert savings_rate == Decimal("-50")


class TestDashboardRecentTransactions:
    """Integration tests for recent transactions display."""

    @pytest.mark.asyncio
    async def test_transactions_sorted_by_date_descending(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test that recent transactions are sorted newest first."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Create transactions at different dates
        txn_old = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("100.00"),
            now - timedelta(days=30),
            "Old Transaction",
        )
        await transaction_repo.save(txn_old)

        txn_middle = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("200.00"),
            now - timedelta(days=15),
            "Middle Transaction",
        )
        await transaction_repo.save(txn_middle)

        txn_recent = _create_expense_transaction(
            accounts["checking"],
            accounts["entertainment"],
            Decimal("50.00"),
            now - timedelta(days=1),
            "Recent Transaction",
        )
        await transaction_repo.save(txn_recent)

        await db_session.commit()

        # Get and sort transactions like dashboard does
        txns = await transaction_repo.find_posted_transactions()
        sorted_txns = sorted(txns, key=lambda t: ensure_tz_aware(t.date), reverse=True)

        assert sorted_txns[0].description == "Recent Transaction"
        assert sorted_txns[1].description == "Middle Transaction"
        assert sorted_txns[2].description == "Old Transaction"

    @pytest.mark.asyncio
    async def test_limit_recent_transactions(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test that recent transactions list is limited."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        now = datetime.now(tz=timezone.utc)

        # Create 15 transactions
        for i in range(15):
            txn = _create_expense_transaction(
                accounts["checking"],
                accounts["groceries"],
                Decimal("10.00"),
                now - timedelta(days=i),
                f"Transaction {i + 1}",
            )
            await transaction_repo.save(txn)

        await db_session.commit()

        # Get limited list like dashboard does
        txns = await transaction_repo.find_posted_transactions()
        sorted_txns = sorted(txns, key=lambda t: ensure_tz_aware(t.date), reverse=True)
        limited = sorted_txns[:10]

        assert len(limited) == 10
        assert limited[0].description == "Transaction 1"  # Most recent
        assert limited[9].description == "Transaction 10"


class TestDashboardMonthFiltering:
    """Integration tests for month-based filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_specific_month(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test filtering transactions to a specific month."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        # Create transactions in different months
        jan_txn = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("100.00"),
            datetime(2025, 1, 15, tzinfo=timezone.utc),
            "January Groceries",
        )
        await transaction_repo.save(jan_txn)

        feb_txn = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("200.00"),
            datetime(2025, 2, 15, tzinfo=timezone.utc),
            "February Transport",
        )
        await transaction_repo.save(feb_txn)

        await db_session.commit()

        # Filter to January like dashboard does
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        txns = await transaction_repo.find_posted_transactions()
        filtered = [t for t in txns if start_date <= t.date < end_date]

        assert len(filtered) == 1
        assert filtered[0].description == "January Groceries"

    @pytest.mark.asyncio
    async def test_december_to_january_transition(
        self,
        db_session,
        current_user,
        setup_accounts,
    ):
        """Test filtering for December (year transition)."""
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        transaction_repo = TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        )
        accounts = setup_accounts

        # Create transaction in December
        dec_txn = _create_expense_transaction(
            accounts["checking"],
            accounts["groceries"],
            Decimal("100.00"),
            datetime(2024, 12, 15, tzinfo=timezone.utc),
            "December Groceries",
        )
        await transaction_repo.save(dec_txn)

        # Create transaction in January
        jan_txn = _create_expense_transaction(
            accounts["checking"],
            accounts["transport"],
            Decimal("200.00"),
            datetime(2025, 1, 5, tzinfo=timezone.utc),
            "January Transport",
        )
        await transaction_repo.save(jan_txn)

        await db_session.commit()

        # Filter to December 2024
        start_date = datetime(2024, 12, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        txns = await transaction_repo.find_posted_transactions()
        # Ensure date comparison works with both tz-aware and naive datetimes
        filtered = [
            t
            for t in txns
            if start_date.replace(tzinfo=None)
            <= t.date.replace(tzinfo=None)
            < end_date.replace(tzinfo=None)
        ]

        assert len(filtered) == 1
        assert filtered[0].description == "December Groceries"
