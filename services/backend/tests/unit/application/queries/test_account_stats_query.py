"""Unit tests for AccountStatsQuery."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.queries.accounting import AccountStatsQuery
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
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
def mock_balance_service():
    """Create a mock balance service."""
    service = MagicMock()
    service.calculate_balance = MagicMock(
        return_value=Money(amount=Decimal("1000.00"), currency=Currency(code="EUR")),
    )
    return service


@pytest.fixture
def sample_checking_account():
    """Create a sample checking account."""
    account = MagicMock(spec=Account)
    account.id = uuid4()
    account.name = "Checking Account"
    account.account_number = "1200"
    account.account_type = AccountType.ASSET
    account.default_currency = Currency(code="EUR")
    account.is_active = True
    return account


def create_mock_entry(account_id, debit: Decimal, credit: Decimal):
    """Create a mock journal entry with Money objects."""
    entry = MagicMock()
    # Entry has account object with id, not account_id directly
    entry.account = MagicMock()
    entry.account.id = account_id
    # Use Money objects like the real domain model
    entry.debit = Money(amount=debit, currency=Currency(code="EUR"))
    entry.credit = Money(amount=credit, currency=Currency(code="EUR"))
    return entry


def create_mock_transaction(
    date: datetime,
    entries: list,
    is_posted: bool = True,
    account_ids: list | None = None,
):
    """Create a mock transaction.

    Args:
        date: Transaction date
        entries: List of mock entries
        is_posted: Whether transaction is posted
        account_ids: List of account IDs this transaction involves
    """
    txn = MagicMock()
    txn.id = uuid4()
    txn.date = date
    txn.entries = entries
    txn.is_posted = is_posted

    # Set up involves_account to check if account ID is in the list
    if account_ids:
        txn.involves_account = MagicMock(
            side_effect=lambda acc: acc.id in account_ids,
        )
    else:
        txn.involves_account = MagicMock(return_value=False)

    return txn


class TestAccountStatsQuery:
    """Tests for AccountStatsQuery."""

    @pytest.mark.asyncio
    async def test_execute_returns_stats_for_account(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
        sample_checking_account,
    ):
        """Test that execute returns comprehensive stats."""
        # Setup
        mock_account_repo.find_by_id.return_value = sample_checking_account

        now = datetime.now(timezone.utc)
        entries1 = [
            create_mock_entry(sample_checking_account.id, Decimal("0"), Decimal("500")),  # credit
        ]
        entries2 = [
            create_mock_entry(sample_checking_account.id, Decimal("100"), Decimal("0")),  # debit
        ]

        txn1 = create_mock_transaction(
            now - timedelta(days=5),
            entries1,
            is_posted=True,
            account_ids=[sample_checking_account.id],
        )
        txn2 = create_mock_transaction(
            now - timedelta(days=2),
            entries2,
            is_posted=True,
            account_ids=[sample_checking_account.id],
        )

        mock_transaction_repo.find_all.return_value = [txn1, txn2]

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        # Execute
        result = await query.execute(account_id=sample_checking_account.id)

        # Verify
        assert result.account_id == sample_checking_account.id
        assert result.account_name == "Checking Account"
        assert result.account_number == "1200"
        assert result.account_type == "asset"
        assert result.currency == "EUR"
        assert result.balance == Decimal("1000.00")
        assert result.balance_includes_drafts is True
        assert result.transaction_count == 2
        assert result.posted_count == 2
        assert result.draft_count == 0
        assert result.total_debits == Decimal("100")
        assert result.total_credits == Decimal("500")
        assert result.net_flow == Decimal("-400")  # 100 - 500 (debits - credits)
        assert result.first_transaction_date is not None
        assert result.last_transaction_date is not None

    @pytest.mark.asyncio
    async def test_execute_raises_error_for_nonexistent_account(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
    ):
        """Test that execute raises ValueError for nonexistent account."""
        mock_account_repo.find_by_id.return_value = None

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        with pytest.raises(AccountNotFoundError):
            await query.execute(account_id=uuid4())

    @pytest.mark.asyncio
    async def test_execute_with_days_filter(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
        sample_checking_account,
    ):
        """Test that execute respects days filter for flow stats."""
        mock_account_repo.find_by_id.return_value = sample_checking_account

        now = datetime.now(timezone.utc)

        # Old transaction (outside 7 days)
        old_entries = [
            create_mock_entry(sample_checking_account.id, Decimal("0"), Decimal("1000")),
        ]
        old_txn = create_mock_transaction(
            now - timedelta(days=30),
            old_entries,
            is_posted=True,
            account_ids=[sample_checking_account.id],
        )

        # Recent transaction (within 7 days)
        recent_entries = [
            create_mock_entry(sample_checking_account.id, Decimal("100"), Decimal("0")),
        ]
        recent_txn = create_mock_transaction(
            now - timedelta(days=3),
            recent_entries,
            is_posted=True,
            account_ids=[sample_checking_account.id],
        )

        mock_transaction_repo.find_all.return_value = [old_txn, recent_txn]

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        # Execute with 7-day filter
        result = await query.execute(account_id=sample_checking_account.id, days=7)

        # Only recent transaction should be in flow stats
        assert result.transaction_count == 1
        assert result.total_debits == Decimal("100")
        assert result.total_credits == Decimal("0")
        assert result.period_days == 7
        assert result.period_start is not None
        assert result.period_end is not None

    @pytest.mark.asyncio
    async def test_execute_excludes_drafts_when_requested(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
        sample_checking_account,
    ):
        """Test that execute can exclude draft transactions."""
        mock_account_repo.find_by_id.return_value = sample_checking_account

        now = datetime.now(timezone.utc)

        posted_entries = [
            create_mock_entry(sample_checking_account.id, Decimal("0"), Decimal("500")),
        ]
        posted_txn = create_mock_transaction(
            now - timedelta(days=5),
            posted_entries,
            is_posted=True,
            account_ids=[sample_checking_account.id],
        )

        draft_entries = [
            create_mock_entry(sample_checking_account.id, Decimal("200"), Decimal("0")),
        ]
        draft_txn = create_mock_transaction(
            now - timedelta(days=2),
            draft_entries,
            is_posted=False,
            account_ids=[sample_checking_account.id],
        )

        mock_transaction_repo.find_all.return_value = [posted_txn, draft_txn]

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        # Execute with include_drafts=False
        result = await query.execute(
            account_id=sample_checking_account.id,
            include_drafts=False,
        )

        # Draft should not be in flow stats
        assert result.transaction_count == 2  # Both counted
        assert result.posted_count == 1
        assert result.draft_count == 1
        # But only posted in flow calculations
        assert result.total_debits == Decimal("0")
        assert result.total_credits == Decimal("500")
        assert result.balance_includes_drafts is False

    @pytest.mark.asyncio
    async def test_execute_with_no_transactions(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
        sample_checking_account,
    ):
        """Test stats for account with no transactions."""
        mock_account_repo.find_by_id.return_value = sample_checking_account
        mock_transaction_repo.find_all.return_value = []
        mock_balance_service.calculate_balance.return_value = Money(
            amount=Decimal("0"),
            currency=Currency(code="EUR"),
        )

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        result = await query.execute(account_id=sample_checking_account.id)

        assert result.transaction_count == 0
        assert result.posted_count == 0
        assert result.draft_count == 0
        assert result.total_debits == Decimal("0")
        assert result.total_credits == Decimal("0")
        assert result.net_flow == Decimal("0")
        assert result.first_transaction_date is None
        assert result.last_transaction_date is None

    @pytest.mark.asyncio
    async def test_to_dict_serialization(
        self,
        mock_account_repo,
        mock_transaction_repo,
        mock_balance_service,
        sample_checking_account,
    ):
        """Test that result can be serialized to dict."""
        mock_account_repo.find_by_id.return_value = sample_checking_account
        mock_transaction_repo.find_all.return_value = []
        mock_balance_service.calculate_balance.return_value = Money(
            amount=Decimal("0"),
            currency=Currency(code="EUR"),
        )

        query = AccountStatsQuery(
            account_repository=mock_account_repo,
            transaction_repository=mock_transaction_repo,
            balance_service=mock_balance_service,
        )

        result = await query.execute(account_id=sample_checking_account.id)
        result_dict = result.to_dict()

        assert "account_id" in result_dict
        assert "balance" in result_dict
        assert "transaction_count" in result_dict
        assert result_dict["balance"] == "0"
