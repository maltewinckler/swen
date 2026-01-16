"""Integration tests for transactions endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


class TestCreateTransaction:
    """Tests for POST /api/v1/transactions (create manual transaction)."""

    @pytest.fixture
    def expense_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
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
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
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
    def income_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Create an income account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Salary",
                "account_number": "4001",
                "account_type": "income",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    def test_create_transaction_expense(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Create an expense transaction successfully."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Test grocery purchase",
                "entries": [
                    {
                        "account_id": expense_account["id"],
                        "debit": "45.99",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "45.99",
                    },
                ],
                "counterparty": "REWE",
                "auto_post": False,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["description"] == "Test grocery purchase"
        assert data["counterparty"] == "REWE"
        assert data["is_posted"] is False
        assert len(data["entries"]) == 2

    def test_create_transaction_and_post(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Create and auto-post a transaction."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Auto-posted expense",
                "entries": [
                    {
                        "account_id": expense_account["id"],
                        "debit": "25.00",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "25.00",
                    },
                ],
                "auto_post": True,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["is_posted"] is True

    def test_create_multi_entry_transaction(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        asset_account: dict,
    ):
        """Create a transaction with multiple debit entries (split purchase)."""
        # Create two expense accounts for split purchase
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Groceries",
                "account_number": "4001",
                "account_type": "expense",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        groceries_account = response.json()

        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Household",
                "account_number": "4002",
                "account_type": "expense",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        household_account = response.json()

        # Create a split transaction: €50 total = €30 groceries + €20 household
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "REWE Split Purchase",
                "entries": [
                    {
                        "account_id": groceries_account["id"],
                        "debit": "30.00",
                        "credit": "0",
                    },
                    {
                        "account_id": household_account["id"],
                        "debit": "20.00",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "50.00",
                    },
                ],
                "counterparty": "REWE",
                "auto_post": True,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["description"] == "REWE Split Purchase"
        assert data["is_posted"] is True
        assert len(data["entries"]) == 3

        # Verify entry details
        debits = [e for e in data["entries"] if e["debit"]]
        credits = [e for e in data["entries"] if e["credit"]]

        assert len(debits) == 2
        assert len(credits) == 1

        # Total debits should equal total credit
        total_debit = sum(float(e["debit"]) for e in debits)
        total_credit = float(credits[0]["credit"])
        assert total_debit == total_credit == 50.00

    def test_create_transaction_unbalanced_entries(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Cannot create transaction with unbalanced entries."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Unbalanced",
                "entries": [
                    {
                        "account_id": expense_account["id"],
                        "debit": "100.00",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "50.00",  # Doesn't match!
                    },
                ],
            },
        )

        assert response.status_code == 422
        assert "balance" in response.json()["detail"].lower()

    def test_create_transaction_zero_amount(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Cannot create transaction with zero amounts."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Zero amount",
                "entries": [
                    {
                        "account_id": expense_account["id"],
                        "debit": "0",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "0",
                    },
                ],
            },
        )

        assert response.status_code == 422
        assert "non-zero" in response.json()["detail"].lower()

    def test_create_transaction_account_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot create transaction with non-existent account."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Bad account",
                "entries": [
                    {
                        "account_id": fake_id,
                        "debit": "100.00",
                        "credit": "0",
                    },
                    {
                        "account_id": fake_id,
                        "debit": "0",
                        "credit": "100.00",
                    },
                ],
            },
        )

        # AccountNotFoundError maps to 404 (entity not found)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_transaction_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot create transaction without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Unauthorized",
                "entries": [],
            },
        )
        assert response.status_code == 401


class TestCreateSimpleTransaction:
    """Tests for POST /api/v1/transactions/simple."""

    @pytest.fixture
    def expense_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Create an expense account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Other Expenses",
                "account_number": "6099",
                "account_type": "expense",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    def income_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Create an income account for testing."""
        response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=auth_headers,
            json={
                "name": "Other Income",
                "account_number": "4099",
                "account_type": "income",
                "currency": "EUR",
            },
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    def asset_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
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

    def test_create_simple_expense(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Create a simple expense transaction."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Coffee shop",
                "amount": "-5.50",
                "counterparty": "Starbucks",
                "auto_post": True,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["description"] == "Coffee shop"
        assert data["counterparty"] == "Starbucks"
        assert data["is_posted"] is True
        assert len(data["entries"]) == 2

    def test_create_simple_income(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        income_account: dict,
        asset_account: dict,
    ):
        """Create a simple income transaction."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Salary payment",
                "amount": "3500.00",
                "counterparty": "ACME Corp",
                "auto_post": False,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["description"] == "Salary payment"
        assert data["is_posted"] is False

    def test_create_simple_with_specific_accounts(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        expense_account: dict,
        asset_account: dict,
    ):
        """Create simple transaction with specific account hints."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Specific accounts",
                "amount": "-100.00",
                "asset_account": "1001",
                "category_account": "6099",
            },
        )

        assert response.status_code == 201

    def test_create_simple_zero_amount(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
        asset_account: dict,
        expense_account: dict,
    ):
        """Cannot create simple transaction with zero amount."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Zero",
                "amount": "0",
            },
        )

        # ValidationError from command maps to 400
        assert response.status_code == 400
        assert "non-zero" in response.json()["detail"].lower()

    def test_create_simple_no_asset_account(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot create simple transaction without any asset accounts."""
        # Don't create any accounts - command should fail with AccountNotFoundError
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=auth_headers,
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "No accounts",
                "amount": "-10.00",
            },
        )

        # AccountNotFoundError maps to 404 (the requested account doesn't exist)
        assert response.status_code == 404
        assert "account" in response.json()["detail"].lower()

    def test_create_simple_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot create simple transaction without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            json={
                "date": datetime.now(tz=timezone.utc).isoformat(),
                "description": "Unauthorized",
                "amount": "-10.00",
            },
        )
        assert response.status_code == 401


class TestListTransactions:
    """Tests for GET /api/v1/transactions."""

    def test_list_transactions_empty(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """List transactions returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["transactions"] == []
        assert data["total"] == 0
        assert data["draft_count"] == 0
        assert data["posted_count"] == 0

    def test_list_transactions_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot list transactions without auth."""
        response = test_client.get(f"{api_v1_prefix}/transactions")
        assert response.status_code == 401

    def test_list_transactions_with_filters(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """List transactions accepts filter parameters."""
        response = test_client.get(
            f"{api_v1_prefix}/transactions",
            headers=auth_headers,
            params={
                "days": 30,
                "limit": 10,
                "status": "posted",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty but valid response
        assert "transactions" in data
        assert "total" in data


class TestGetTransaction:
    """Tests for GET /api/v1/transactions/{transaction_id}."""

    def test_get_transaction_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Get non-existent transaction returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"{api_v1_prefix}/transactions/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_transaction_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot get transaction without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"{api_v1_prefix}/transactions/{fake_id}")
        assert response.status_code == 401


class TestPostTransaction:
    """Tests for POST /api/v1/transactions/{transaction_id}/post."""

    def test_post_transaction_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Post non-existent transaction returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.post(
            f"{api_v1_prefix}/transactions/{fake_id}/post",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_post_transaction_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot post transaction without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.post(f"{api_v1_prefix}/transactions/{fake_id}/post")
        assert response.status_code == 401


class TestUnpostTransaction:
    """Tests for POST /api/v1/transactions/{transaction_id}/unpost."""

    def test_unpost_transaction_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Unpost non-existent transaction returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.post(
            f"{api_v1_prefix}/transactions/{fake_id}/unpost",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_unpost_transaction_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot unpost transaction without auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.post(f"{api_v1_prefix}/transactions/{fake_id}/unpost")
        assert response.status_code == 401
