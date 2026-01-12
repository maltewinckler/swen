"""Integration tests for dashboard endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary."""

    def test_get_summary_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get dashboard summary for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/summary", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        # Money values are returned as strings for precision
        assert data["total_income"] == "0"
        assert data["total_expenses"] == "0"
        assert data["net_income"] == "0"
        assert data["account_balances"] == []
        assert data["category_spending"] == []
        assert data["recent_transactions"] == []
        assert data["draft_count"] == 0
        assert data["posted_count"] == 0

    def test_get_summary_with_days_filter(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get dashboard summary with days filter."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/summary",
            headers=auth_headers,
            params={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data

    def test_get_summary_with_month_filter(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get dashboard summary with month filter."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/summary",
            headers=auth_headers,
            params={"month": "2024-01"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data

    def test_get_summary_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot get dashboard summary without auth."""
        response = test_client.get(f"{api_v1_prefix}/dashboard/summary")
        assert response.status_code == 401


class TestDashboardSpending:
    """Tests for GET /api/v1/dashboard/spending."""

    def test_get_spending_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get spending breakdown for new user with no data."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/spending", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        # Money values are returned as strings for precision
        assert data["total_spending"] == "0"
        assert data["categories"] == []

    def test_get_spending_with_filters(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get spending breakdown with filters."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/spending",
            headers=auth_headers,
            params={"days": 60},
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_label" in data
        assert "total_spending" in data

    def test_get_spending_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot get spending breakdown without auth."""
        response = test_client.get(f"{api_v1_prefix}/dashboard/spending")
        assert response.status_code == 401


class TestDashboardBalances:
    """Tests for GET /api/v1/dashboard/balances."""

    def test_get_balances_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get balances for new user with no accounts."""
        response = test_client.get(
            f"{api_v1_prefix}/dashboard/balances", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["balances"] == []
        # Money values are returned as strings for precision
        assert data["total_assets"] == "0"

    def test_get_balances_with_accounts(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get balances after creating accounts."""
        # Create an asset account
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Bank Account",
                "account_number": "1000",
                "account_type": "asset",
                "currency": "EUR",
            },
        )

        response = test_client.get(
            f"{api_v1_prefix}/dashboard/balances", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Balance should be 0 (no transactions)
        assert "balances" in data
        assert "total_assets" in data

    def test_get_balances_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot get balances without auth."""
        response = test_client.get(f"{api_v1_prefix}/dashboard/balances")
        assert response.status_code == 401
