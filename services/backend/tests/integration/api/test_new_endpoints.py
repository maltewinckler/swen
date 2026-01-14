"""Integration tests for newly added endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


class TestUpdateTransaction:
    """Tests for PUT /api/v1/transactions/{id}."""

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
    def created_transaction(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Create a transaction for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Original description",
                "entries": [
                    {
                        "account_id": expense_account["id"],
                        "debit": "50.00",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "50.00",
                    },
                ],
                "counterparty": "Original Store",
                "auto_post": False,
            },
        )
        assert response.status_code == 201
        return response.json()

    def test_update_transaction_description(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        created_transaction: dict,
    ):
        """Update transaction description."""
        txn_id = created_transaction["id"]
        response = test_client.put(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=auth_headers,
            json={"description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_transaction_counterparty(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        created_transaction: dict,
    ):
        """Update transaction counterparty."""
        txn_id = created_transaction["id"]
        response = test_client.put(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=auth_headers,
            json={"counterparty": "New Store Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["counterparty"] == "New Store Name"

    def test_update_transaction_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Cannot update non-existent transaction."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.put(
            f"{api_v1_prefix}/transactions/{fake_id}",
            headers=auth_headers,
            json={"description": "Test"},
        )

        assert response.status_code == 404

    def test_update_transaction_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot update transaction without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.put(
            f"{api_v1_prefix}/transactions/{fake_id}",
            json={"description": "Test"},
        )

        assert response.status_code == 401


class TestInitChartOfAccounts:
    """Tests for POST /api/v1/accounts/init-chart."""

    def test_init_chart_creates_accounts(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Initialize chart of accounts creates default accounts."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["skipped"] is False
        assert data["accounts_created"] > 0
        assert "by_type" in data

    def test_init_chart_is_idempotent(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Second call returns skipped status."""
        # First call
        response1 = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Second call
        response2 = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=auth_headers,
        )
        # Returns 201 but with skipped=True
        assert response2.status_code == 201
        data = response2.json()
        assert data["skipped"] is True

    def test_init_chart_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot init chart without auth."""
        response = test_client.post(f"{api_v1_prefix}/accounts/init-chart")
        assert response.status_code == 401


class TestExports:
    """Tests for GET /api/v1/exports/*."""

    def test_export_transactions_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Export transactions returns empty list for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/exports/transactions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["count"] == 0

    def test_export_transactions_with_filters(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Export transactions accepts filter parameters."""
        response = test_client.get(
            f"{api_v1_prefix}/exports/transactions",
            headers=auth_headers,
            params={"days": 30, "status": "posted"},
        )

        assert response.status_code == 200

    def test_export_accounts_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Export accounts returns empty list for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/exports/accounts",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert "count" in data

    def test_export_full(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Full export returns all data types."""
        response = test_client.get(
            f"{api_v1_prefix}/exports/full",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "accounts" in data
        assert "mappings" in data
        assert "transaction_count" in data

    def test_export_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot export without auth."""
        response = test_client.get(f"{api_v1_prefix}/exports/transactions")
        assert response.status_code == 401


class TestMappings:
    """Tests for GET /api/v1/mappings/*."""

    def test_list_mappings_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """List mappings returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/mappings",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mappings"] == []
        assert data["count"] == 0

    def test_get_mapping_by_iban_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get mapping by IBAN returns 404 when not found."""
        response = test_client.get(
            f"{api_v1_prefix}/mappings/DE89370400440532013000",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_mappings_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot list mappings without auth."""
        response = test_client.get(f"{api_v1_prefix}/mappings")
        assert response.status_code == 401


class TestImports:
    """Tests for GET /api/v1/imports/*."""

    def test_list_imports_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """List imports returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/imports",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imports"] == []
        assert data["count"] == 0
        assert "status_counts" in data

    def test_list_imports_with_filters(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """List imports accepts filter parameters."""
        response = test_client.get(
            f"{api_v1_prefix}/imports",
            headers=auth_headers,
            params={"days": 30, "limit": 10, "failed_only": True},
        )

        assert response.status_code == 200

    def test_import_statistics(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get import statistics."""
        response = test_client.get(
            f"{api_v1_prefix}/imports/statistics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "success" in data
        assert "failed" in data

    def test_imports_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot list imports without auth."""
        response = test_client.get(f"{api_v1_prefix}/imports")
        assert response.status_code == 401


class TestPreferences:
    """Tests for /api/v1/preferences/*."""

    def test_get_preferences(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Get user preferences."""
        response = test_client.get(
            f"{api_v1_prefix}/preferences",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "sync_settings" in data
        assert "display_settings" in data
        assert "auto_post_transactions" in data["sync_settings"]
        assert "default_currency" in data["sync_settings"]
        assert "show_draft_transactions" in data["display_settings"]

    def test_update_preferences(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Update user preferences."""
        response = test_client.patch(
            f"{api_v1_prefix}/preferences",
            headers=auth_headers,
            json={"auto_post_transactions": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sync_settings"]["auto_post_transactions"] is True

    def test_update_preferences_multiple_fields(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Update multiple preferences at once."""
        response = test_client.patch(
            f"{api_v1_prefix}/preferences",
            headers=auth_headers,
            json={
                "auto_post_transactions": False,
                "default_currency": "USD",
                "show_draft_transactions": False,
                "default_date_range_days": 90,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sync_settings"]["auto_post_transactions"] is False
        assert data["sync_settings"]["default_currency"] == "USD"
        assert data["display_settings"]["show_draft_transactions"] is False
        assert data["display_settings"]["default_date_range_days"] == 90

    def test_update_preferences_empty_body(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Cannot update with empty body."""
        response = test_client.patch(
            f"{api_v1_prefix}/preferences",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 400

    def test_reset_preferences(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str,
    ):
        """Reset preferences to defaults."""
        # First update some preferences
        test_client.patch(
            f"{api_v1_prefix}/preferences",
            headers=auth_headers,
            json={"auto_post_transactions": True, "default_currency": "USD"},
        )

        # Then reset
        response = test_client.post(
            f"{api_v1_prefix}/preferences/reset",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should be back to defaults
        assert data["sync_settings"]["auto_post_transactions"] is False
        assert data["sync_settings"]["default_currency"] == "EUR"

    def test_preferences_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot access preferences without auth."""
        response = test_client.get(f"{api_v1_prefix}/preferences")
        assert response.status_code == 401

