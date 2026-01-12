"""Unit tests for ExportReportQuery.

These tests verify the query orchestration without requiring
a real database.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from swen.application.dtos.analytics import (
    BreakdownItem,
    CategoryTimeSeriesDataPoint,
    CategoryTimeSeriesResult,
    IncomeBreakdownResult,
    MonthComparisonResult,
    SpendingBreakdownResult,
    TimeSeriesDataPoint,
    TimeSeriesResult,
)
from swen.application.queries.export_report_query import ExportReportQuery
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping


class TestExportReportQuery:
    """Test suite for ExportReportQuery."""

    @pytest.fixture
    def mock_analytics_port(self) -> AsyncMock:
        """Create mock analytics port with default responses."""
        port = AsyncMock()

        # Spending breakdown
        port.spending_breakdown.return_value = SpendingBreakdownResult(
            period_label="December 2024",
            items=[
                BreakdownItem(
                    category="Groceries",
                    amount=Decimal("500.00"),
                    percentage=Decimal("50.0"),
                    account_id=str(uuid4()),
                ),
            ],
            total=Decimal("1000.00"),
            currency="EUR",
            category_count=1,
        )

        # Income breakdown
        port.income_breakdown.return_value = IncomeBreakdownResult(
            period_label="December 2024",
            items=[],
            total=Decimal("3000.00"),
            currency="EUR",
        )

        # Net worth over time
        port.net_worth_over_time.return_value = TimeSeriesResult(
            data_points=[
                TimeSeriesDataPoint(
                    period="2024-12",
                    period_label="December 2024",
                    value=Decimal("25000.00"),
                ),
            ],
            currency="EUR",
            total=Decimal("25000.00"),
            average=Decimal("25000.00"),
        )

        # Month comparison
        port.month_comparison.return_value = MonthComparisonResult(
            current_month="December 2024",
            previous_month="November 2024",
            currency="EUR",
            current_income=Decimal("3000.00"),
            previous_income=Decimal("2800.00"),
            income_change=Decimal("200.00"),
            income_change_percentage=Decimal("7.1"),
            current_spending=Decimal("1000.00"),
            previous_spending=Decimal("1200.00"),
            spending_change=Decimal("-200.00"),
            spending_change_percentage=Decimal("-16.7"),
            current_net=Decimal("2000.00"),
            previous_net=Decimal("1600.00"),
            net_change=Decimal("400.00"),
            net_change_percentage=Decimal("25.0"),
            category_comparisons=[],
        )

        # Balance history
        port.balance_history_over_time.return_value = CategoryTimeSeriesResult(
            data_points=[
                CategoryTimeSeriesDataPoint(
                    period="2024-12",
                    period_label="December 2024",
                    categories={"DKB Checking": Decimal("5000.00")},
                    total=Decimal("5000.00"),
                ),
            ],
            categories=["DKB Checking"],
            currency="EUR",
        )

        return port

    @pytest.fixture
    def mock_transaction_repo(self) -> AsyncMock:
        """Create mock transaction repository."""
        repo = AsyncMock()
        repo.find_all.return_value = []
        repo.find_posted_transactions.return_value = []
        return repo

    @pytest.fixture
    def mock_account_repo(self) -> AsyncMock:
        """Create mock account repository."""
        repo = AsyncMock()

        user_id = uuid4()
        accounts = [
            Account(
                name="DKB Checking",
                account_type=AccountType.ASSET,
                account_number="1000",
                default_currency=Currency("EUR"),
                user_id=user_id,
            ),
            Account(
                name="Groceries",
                account_type=AccountType.EXPENSE,
                account_number="4200",
                default_currency=Currency("EUR"),
                user_id=user_id,
            ),
        ]
        repo.find_all.return_value = accounts
        return repo

    @pytest.fixture
    def mock_mapping_repo(self) -> AsyncMock:
        """Create mock mapping repository."""
        repo = AsyncMock()
        repo.find_all.return_value = []
        return repo

    @pytest.fixture
    def query(
        self,
        mock_analytics_port,
        mock_transaction_repo,
        mock_account_repo,
        mock_mapping_repo,
    ) -> ExportReportQuery:
        """Create query instance with mocked dependencies."""
        return ExportReportQuery(
            analytics_read_port=mock_analytics_port,
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
            mapping_repository=mock_mapping_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_export_report_data(self, query):
        """Test that execute() returns ExportReportData with all sections."""
        result = await query.execute()

        assert result is not None
        assert result.summary is not None
        assert result.transactions is not None
        assert result.accounts is not None
        assert result.mappings is not None

    @pytest.mark.asyncio
    async def test_execute_with_days_parameter(
        self, query, mock_analytics_port
    ):
        """Test that days parameter affects date range calculation."""
        result = await query.execute(days=30)

        # Should calculate date range for last 30 days
        assert result.summary.period_label == "Last 30 days"

    @pytest.mark.asyncio
    async def test_execute_with_month_parameter(
        self, query, mock_analytics_port
    ):
        """Test that month parameter sets correct period."""
        result = await query.execute(month="2024-12")

        assert "December 2024" in result.summary.period_label

    @pytest.mark.asyncio
    async def test_execute_with_custom_date_range(self, query):
        """Test that custom date range is handled correctly."""
        start = date(2024, 1, 1)
        end = date(2024, 6, 30)

        result = await query.execute(start_date=start, end_date=end)

        assert start.strftime("%d %b %Y") in result.summary.period_label
        assert end.strftime("%d %b %Y") in result.summary.period_label

    @pytest.mark.asyncio
    async def test_execute_all_time_label(self, query):
        """Test that no date params gives 'All Time' label."""
        result = await query.execute()

        assert result.summary.period_label == "All Time"

    @pytest.mark.asyncio
    async def test_summary_includes_income_and_expenses(
        self, query, mock_analytics_port
    ):
        """Test that summary includes calculated income and expenses."""
        result = await query.execute()

        assert result.summary.total_income == Decimal("3000.00")
        assert result.summary.total_expenses == Decimal("1000.00")
        assert result.summary.net_income == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_summary_includes_net_worth(self, query):
        """Test that summary includes net worth from latest data point."""
        result = await query.execute()

        assert result.summary.net_worth == Decimal("25000.00")

    @pytest.mark.asyncio
    async def test_summary_includes_savings_rate(self, query):
        """Test that savings rate is calculated correctly."""
        result = await query.execute()

        # Savings rate = (income - expenses) / income * 100
        # = (3000 - 1000) / 3000 * 100 = 66.67%
        expected_rate = Decimal("2000") / Decimal("3000") * 100
        assert result.summary.savings_rate == expected_rate

    @pytest.mark.asyncio
    async def test_accounts_are_converted_to_dtos(
        self, query, mock_account_repo
    ):
        """Test that accounts are converted to AccountExportDTO."""
        result = await query.execute()

        assert len(result.accounts) == 2
        account_names = [a.name for a in result.accounts]
        assert "DKB Checking" in account_names
        assert "Groceries" in account_names

    @pytest.mark.asyncio
    async def test_mappings_include_resolved_account_names(
        self, query, mock_mapping_repo, mock_account_repo
    ):
        """Test that mappings include resolved account names."""
        # Setup mapping that references an account
        user_id = uuid4()
        accounts = mock_account_repo.find_all.return_value
        checking_account = accounts[0]  # DKB Checking

        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=checking_account.id,
            account_name="Personal Checking",
            user_id=user_id,
        )
        mock_mapping_repo.find_all.return_value = [mapping]

        result = await query.execute()

        assert len(result.mappings) == 1
        mapping_dto = result.mappings[0]
        assert mapping_dto.iban == "DE89370400440532013000"
        assert mapping_dto.bank_account_name == "Personal Checking"
        assert mapping_dto.accounting_account_name == "DKB Checking"
        assert mapping_dto.accounting_account_number == "1000"

    @pytest.mark.asyncio
    async def test_mappings_fallback_to_uuid_if_account_not_found(
        self, query, mock_mapping_repo, mock_account_repo
    ):
        """Test that mappings show UUID if account lookup fails."""
        user_id = uuid4()
        unknown_account_id = uuid4()

        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=unknown_account_id,
            account_name="Unknown Account",
            user_id=user_id,
        )
        mock_mapping_repo.find_all.return_value = [mapping]

        result = await query.execute()

        assert len(result.mappings) == 1
        # Should fallback to UUID string
        assert result.mappings[0].accounting_account_name == str(unknown_account_id)

    @pytest.mark.asyncio
    async def test_include_drafts_parameter_is_passed(
        self, query, mock_transaction_repo
    ):
        """Test that include_drafts parameter affects transaction fetching."""
        # With include_drafts=True
        await query.execute(include_drafts=True)
        mock_transaction_repo.find_all.assert_awaited()

        mock_transaction_repo.reset_mock()

        # With include_drafts=False
        await query.execute(include_drafts=False)
        mock_transaction_repo.find_posted_transactions.assert_awaited()


class TestExportReportQueryDateRangeResolution:
    """Tests for date range resolution logic."""

    @pytest.fixture
    def query(self) -> ExportReportQuery:
        """Create query with minimal mocks for date range testing."""
        return ExportReportQuery(
            analytics_read_port=AsyncMock(),
            transaction_repository=AsyncMock(),
            account_repository=AsyncMock(),
            mapping_repository=AsyncMock(),
        )

    def test_resolve_custom_date_range(self, query):
        """Test custom date range resolution."""
        start = date(2024, 1, 1)
        end = date(2024, 6, 30)

        resolved_start, resolved_end, label = query._resolve_date_range(
            start_date=start,
            end_date=end,
            days=None,
            month=None,
        )

        assert resolved_start == start
        assert resolved_end == end
        assert "01 Jan 2024" in label
        assert "30 Jun 2024" in label

    def test_resolve_days_parameter(self, query):
        """Test days parameter resolution."""
        resolved_start, resolved_end, label = query._resolve_date_range(
            start_date=None,
            end_date=None,
            days=30,
            month=None,
        )

        assert resolved_start is not None
        assert resolved_end == date.today()
        assert label == "Last 30 days"

    def test_resolve_month_parameter(self, query):
        """Test month parameter resolution."""
        resolved_start, resolved_end, label = query._resolve_date_range(
            start_date=None,
            end_date=None,
            days=None,
            month="2024-12",
        )

        assert resolved_start == date(2024, 12, 1)
        assert resolved_end == date(2024, 12, 31)
        assert "December 2024" in label

    def test_resolve_all_time(self, query):
        """Test all-time (no params) resolution."""
        resolved_start, resolved_end, label = query._resolve_date_range(
            start_date=None,
            end_date=None,
            days=None,
            month=None,
        )

        assert resolved_start is None
        assert resolved_end is None
        assert label == "All Time"

    def test_custom_range_takes_priority(self, query):
        """Test that custom range takes priority over days and month."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        resolved_start, resolved_end, label = query._resolve_date_range(
            start_date=start,
            end_date=end,
            days=30,  # Should be ignored
            month="2024-06",  # Should be ignored
        )

        assert resolved_start == start
        assert resolved_end == end


class TestExportReportQueryFromFactory:
    """Tests for factory method."""

    def test_from_factory_creates_query(self):
        """Test that from_factory creates a properly configured query."""
        mock_factory = Mock()
        mock_factory.analytics_read_port.return_value = AsyncMock()
        mock_factory.transaction_repository.return_value = AsyncMock()
        mock_factory.account_repository.return_value = AsyncMock()
        mock_factory.account_mapping_repository.return_value = AsyncMock()

        query = ExportReportQuery.from_factory(mock_factory)

        assert query is not None
        mock_factory.analytics_read_port.assert_called_once()
        mock_factory.transaction_repository.assert_called_once()
        mock_factory.account_repository.assert_called_once()
        mock_factory.account_mapping_repository.assert_called_once()

