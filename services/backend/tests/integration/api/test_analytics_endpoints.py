"""Integration tests for analytics endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestSpendingOverTime:
    """Tests for GET /api/v1/analytics/spending/over-time."""

    def test_spending_over_time_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending over time for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "categories" in data
        assert "currency" in data
        assert data["categories"] == []  # No expense categories yet
        # Should have 12 months of data points by default
        assert len(data["data_points"]) == 12

    def test_spending_over_time_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/over-time",
            headers=auth_headers,
            params={"months": 6},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 6

    def test_spending_over_time_with_end_month(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending with specific end month."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/over-time",
            headers=auth_headers,
            params={"months": 3, "end_month": "2024-06"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 3
        # Verify periods are correct
        periods = [dp["period"] for dp in data["data_points"]]
        assert "2024-04" in periods
        assert "2024-05" in periods
        assert "2024-06" in periods

    def test_spending_over_time_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get spending over time without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/spending/over-time")
        assert response.status_code == 401


class TestIncomeOverTime:
    """Tests for GET /api/v1/analytics/income/over-time."""

    def test_income_over_time_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get income over time for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "currency" in data
        assert "total" in data
        assert "average" in data
        assert data["total"] == "0"
        assert data["average"] == "0"
        # Should have 12 months of data points by default
        assert len(data["data_points"]) == 12

    def test_income_over_time_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get income with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/over-time",
            headers=auth_headers,
            params={"months": 24},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 24

    def test_income_over_time_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get income over time without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/income/over-time")
        assert response.status_code == 401


class TestSpendingBreakdown:
    """Tests for GET /api/v1/analytics/spending/breakdown."""

    def test_spending_breakdown_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending breakdown for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        assert "items" in data
        assert "total" in data
        assert "currency" in data
        assert data["items"] == []
        assert data["total"] == "0"

    def test_spending_breakdown_with_month_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending breakdown for specific month."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown",
            headers=auth_headers,
            params={"month": "2024-06"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "June 2024" in data["period_label"]

    def test_spending_breakdown_with_days_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get spending breakdown for last N days."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown",
            headers=auth_headers,
            params={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()

        assert "Last 30 days" in data["period_label"]

    def test_spending_breakdown_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get spending breakdown without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/spending/breakdown")
        assert response.status_code == 401


class TestNetIncomeOverTime:
    """Tests for GET /api/v1/analytics/net-income/over-time."""

    def test_net_income_over_time_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get net income over time for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/net-income/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "currency" in data
        assert "total" in data
        assert "average" in data
        assert "min_value" in data
        assert "max_value" in data
        # All values should be 0 for empty data
        assert data["total"] == "0"
        assert len(data["data_points"]) == 12

    def test_net_income_over_time_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get net income with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/net-income/over-time",
            headers=auth_headers,
            params={"months": 6},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 6

    def test_net_income_over_time_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get net income over time without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/net-income/over-time")
        assert response.status_code == 401


class TestTopExpenses:
    """Tests for GET /api/v1/analytics/spending/top."""

    def test_top_expenses_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get top expenses for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/top", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        assert "items" in data
        assert "total_spending" in data
        assert "months_analyzed" in data
        assert data["items"] == []
        assert data["total_spending"] == "0"
        assert data["months_analyzed"] == 3  # Default

    def test_top_expenses_with_params(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get top expenses with custom parameters."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/top",
            headers=auth_headers,
            params={"months": 6, "top_n": 5},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["months_analyzed"] == 6

    def test_top_expenses_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get top expenses without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/spending/top")
        assert response.status_code == 401


class TestIncomeBreakdown:
    """Tests for GET /api/v1/analytics/income/breakdown."""

    def test_income_breakdown_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get income breakdown for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/breakdown", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        assert "items" in data
        assert "total" in data
        assert "currency" in data
        assert data["items"] == []
        assert data["total"] == "0"

    def test_income_breakdown_with_month_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get income breakdown for specific month."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/breakdown",
            headers=auth_headers,
            params={"month": "2024-06"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "June 2024" in data["period_label"]

    def test_income_breakdown_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get income breakdown without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/income/breakdown")
        assert response.status_code == 401


class TestSavingsRateOverTime:
    """Tests for GET /api/v1/analytics/savings-rate/over-time."""

    def test_savings_rate_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get savings rate for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/savings-rate/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "currency" in data
        assert data["currency"] == "%"  # Percentage, not currency
        assert len(data["data_points"]) == 12

    def test_savings_rate_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get savings rate with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/savings-rate/over-time",
            headers=auth_headers,
            params={"months": 6},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 6

    def test_savings_rate_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get savings rate without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/savings-rate/over-time")
        assert response.status_code == 401


class TestNetWorthOverTime:
    """Tests for GET /api/v1/analytics/net-worth/over-time."""

    def test_net_worth_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get net worth for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/net-worth/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "currency" in data
        assert "total" in data  # Latest net worth
        assert data["total"] == "0"
        assert len(data["data_points"]) == 12

    def test_net_worth_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get net worth with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/net-worth/over-time",
            headers=auth_headers,
            params={"months": 24},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 24

    def test_net_worth_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get net worth without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/net-worth/over-time")
        assert response.status_code == 401


class TestBalancesOverTime:
    """Tests for GET /api/v1/analytics/balances/over-time."""

    def test_balances_over_time_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get balances over time for new user with no accounts."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/balances/over-time", headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "categories" in data
        assert "currency" in data
        assert data["categories"] == []  # No asset accounts yet
        assert len(data["data_points"]) == 12

    def test_balances_over_time_with_months_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get balances with custom months parameter."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/balances/over-time",
            headers=auth_headers,
            params={"months": 6},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data_points"]) == 6

    def test_balances_over_time_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get balances over time without auth."""
        response = test_client.get(f"{api_v1_prefix}/analytics/balances/over-time")
        assert response.status_code == 401


class TestMonthComparison:
    """Tests for GET /api/v1/analytics/comparison/month-over-month."""

    def test_month_comparison_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get month comparison for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/comparison/month-over-month",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "current_month" in data
        assert "previous_month" in data
        assert "current_income" in data
        assert "previous_income" in data
        assert "income_change_percentage" in data
        assert "current_spending" in data
        assert "spending_change_percentage" in data
        assert "category_comparisons" in data

    def test_month_comparison_with_month_param(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get month comparison for specific month."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/comparison/month-over-month",
            headers=auth_headers,
            params={"month": "2024-06"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["current_month"] == "June 2024"
        assert data["previous_month"] == "May 2024"

    def test_month_comparison_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot get month comparison without auth."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/comparison/month-over-month",
        )
        assert response.status_code == 401


class TestAnalyticsWithAccounts:
    """Tests for analytics endpoints with created accounts."""

    @pytest.fixture
    def expense_account(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Create an expense account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    def asset_account(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Create an asset account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Checking",
                "account_number": "1001",
                "account_type": "asset",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    def liability_account(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Create a liability account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Credit Card",
                "account_number": "2001",
                "account_type": "liability",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    def test_balances_over_time_with_asset_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        asset_account: dict,
    ):
        """Get balance history includes created asset accounts."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/balances/over-time",
            headers=auth_headers,
            params={"months": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Should include the asset account in categories
        assert "Checking" in data["categories"]
        assert len(data["data_points"]) == 3

    def test_net_worth_with_accounts(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        asset_account: dict,
        liability_account: dict,
    ):
        """Net worth calculation includes assets and liabilities."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/net-worth/over-time",
            headers=auth_headers,
            params={"months": 3},
        )

        assert response.status_code == 200
        data = response.json()

        assert "data_points" in data
        assert "currency" in data
        assert data["currency"] == "EUR"
        # With no transactions, net worth is 0 (assets - liabilities = 0 - 0)
        assert data["total"] == "0"

    def test_spending_breakdown_empty_with_expense_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
    ):
        """Spending breakdown returns empty when no transactions."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # No transactions, so breakdown is empty
        assert data["items"] == []
        assert data["total"] == "0"

    def test_top_expenses_empty_with_expense_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
    ):
        """Top expenses returns empty when no transactions."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/top",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # No transactions, so items are empty
        assert data["items"] == []
        assert data["total_spending"] == "0"


class TestAnalyticsValidation:
    """Tests for parameter validation on analytics endpoints."""

    def test_months_param_min_value(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Months parameter must be at least 1."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/over-time",
            headers=auth_headers,
            params={"months": 0},
        )

        assert response.status_code == 422

    def test_months_param_max_value(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Months parameter must be at most 60."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/income/over-time",
            headers=auth_headers,
            params={"months": 100},
        )

        assert response.status_code == 422

    def test_invalid_month_format(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Month parameter must be in YYYY-MM format."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown",
            headers=auth_headers,
            params={"month": "2024-1"},  # Invalid format
        )

        assert response.status_code == 422

    def test_days_param_min_value(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Days parameter must be at least 1."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/breakdown",
            headers=auth_headers,
            params={"days": 0},
        )

        assert response.status_code == 422

    def test_top_n_param_validation(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Top N parameter must be between 1 and 50."""
        response = test_client.get(
            f"{api_v1_prefix}/analytics/spending/top",
            headers=auth_headers,
            params={"top_n": 100},
        )

        assert response.status_code == 422

