"""Integration tests for accounts endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestListAccounts:
    """Tests for GET /api/v1/accounts."""

    def test_list_accounts_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """List accounts returns empty for new user."""
        response = test_client.get(f"{api_v1_prefix}/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["accounts"] == []
        assert data["total"] == 0

    def test_list_accounts_with_data(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """List accounts returns created accounts."""
        # Create an account first
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
                "currency": "EUR",
            },
        )

        response = test_client.get(f"{api_v1_prefix}/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["accounts"]) == 1
        assert data["accounts"][0]["name"] == "Groceries"
        assert data["accounts"][0]["account_number"] == "6001"

    def test_list_accounts_filter_by_type(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Filter accounts by type."""
        # Create accounts of different types
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Bank Account",
                "account_number": "1000",
                "account_type": "asset",
            },
        )

        # Filter by expense type
        response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            params={"account_type": "expense"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["accounts"][0]["account_type"] == "expense"

    def test_list_accounts_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot list accounts without auth."""
        response = test_client.get(f"{api_v1_prefix}/accounts")
        assert response.status_code == 401


class TestCreateAccount:
    """Tests for POST /api/v1/accounts."""

    def test_create_account_success(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Successfully create an account."""
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
        data = response.json()

        assert data["name"] == "Groceries"
        assert data["account_number"] == "6001"
        assert data["account_type"] == "expense"
        assert data["currency"] == "EUR"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_account_duplicate_number(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Cannot create account with duplicate number."""
        # Create first account
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )

        # Try to create with same number
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Different Name",
                "account_number": "6001",
                "account_type": "expense",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_account_duplicate_name(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Cannot create account with duplicate name."""
        # Create first account
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )

        # Try to create with same name
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6002",
                "account_type": "expense",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_account_invalid_type(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Cannot create account with invalid type."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Test",
                "account_number": "9999",
                "account_type": "invalid_type",
            },
        )

        assert response.status_code == 400

    def test_create_account_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot create account without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )
        assert response.status_code == 401


class TestGetAccount:
    """Tests for GET /api/v1/accounts/{account_id}."""

    def test_get_account_success(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Successfully get an account by ID."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )
        account_id = create_response.json()["id"]

        # Get account
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == account_id
        assert data["name"] == "Groceries"

    def test_get_account_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get non-existent account returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{fake_id}", headers=auth_headers
        )

        assert response.status_code == 404


class TestUpdateAccount:
    """Tests for PATCH /api/v1/accounts/{account_id}."""

    def test_update_account_rename(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Successfully rename an account."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )
        account_id = create_response.json()["id"]

        # Update name
        response = test_client.patch(
            f"{api_v1_prefix}/accounts/{account_id}",
            headers=auth_headers,
            json={"name": "Food & Groceries"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Food & Groceries"
        assert data["account_number"] == "6001"  # Unchanged

    def test_update_account_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Update non-existent account returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.patch(
            f"{api_v1_prefix}/accounts/{fake_id}",
            headers=auth_headers,
            json={"name": "New Name"},
        )

        assert response.status_code == 404


class TestDeactivateAccount:
    """Tests for DELETE /api/v1/accounts/{account_id}."""

    def test_deactivate_account_success(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Successfully deactivate an account."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "6001",
                "account_type": "expense",
            },
        )
        account_id = create_response.json()["id"]

        # Deactivate
        response = test_client.delete(
            f"{api_v1_prefix}/accounts/{account_id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify it's deactivated (not in active_only list)
        list_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            params={"active_only": True},
        )
        assert list_response.json()["total"] == 0

        # But still exists with active_only=False
        list_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            params={"active_only": False},
        )
        assert list_response.json()["total"] == 1
        assert list_response.json()["accounts"][0]["is_active"] is False

    def test_deactivate_account_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Deactivate non-existent account returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.delete(
            f"{api_v1_prefix}/accounts/{fake_id}", headers=auth_headers
        )

        assert response.status_code == 404


class TestBankAccounts:
    """Tests for /api/v1/accounts/bank endpoints."""

    def test_list_bank_accounts_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """List bank accounts returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/accounts/bank", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["accounts"] == []
        assert data["total"] == 0


class TestAccountStats:
    """Tests for GET /api/v1/accounts/{account_id}/stats."""

    def test_get_stats_for_account_no_transactions(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get stats for account with no transactions."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Checking Account",
                "account_number": "1200",
                "account_type": "asset",
            },
        )
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]

        # Get stats
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert data["account_id"] == account_id
        assert data["account_name"] == "Checking Account"
        assert data["account_number"] == "1200"
        assert data["account_type"] == "asset"
        assert data["currency"] == "EUR"
        assert data["balance"] == "0"
        assert data["balance_includes_drafts"] is True
        assert data["transaction_count"] == 0
        assert data["posted_count"] == 0
        assert data["draft_count"] == 0
        assert data["total_debits"] == "0"
        assert data["total_credits"] == "0"
        assert data["net_flow"] == "0"
        assert data["first_transaction_date"] is None
        assert data["last_transaction_date"] is None
        assert data["period_days"] is None  # All-time when no days specified
        assert data["period_end"] is not None  # Should have end date

    def test_get_stats_with_days_filter(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get stats with days filter parameter."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Checking",
                "account_number": "1200",
                "account_type": "asset",
            },
        )
        account_id = create_response.json()["id"]

        # Get stats with 30 day filter
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=auth_headers,
            params={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period_days"] == 30
        assert data["period_start"] is not None
        assert data["period_end"] is not None

    def test_get_stats_exclude_drafts(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get stats excluding draft transactions."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Checking",
                "account_number": "1200",
                "account_type": "asset",
            },
        )
        account_id = create_response.json()["id"]

        # Get stats without drafts
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=auth_headers,
            params={"include_drafts": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["balance_includes_drafts"] is False

    def test_get_stats_not_found(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get stats for non-existent account returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{fake_id}/stats",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_stats_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot get stats without authentication."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{fake_id}/stats",
        )

        assert response.status_code == 401

    def test_get_stats_invalid_days_parameter(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Invalid days parameter returns 422."""
        # Create account
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Checking",
                "account_number": "1200",
                "account_type": "asset",
            },
        )
        account_id = create_response.json()["id"]

        # Negative days
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=auth_headers,
            params={"days": -1},
        )

        assert response.status_code == 422

        # Days too large
        response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=auth_headers,
            params={"days": 99999},
        )

        assert response.status_code == 422
