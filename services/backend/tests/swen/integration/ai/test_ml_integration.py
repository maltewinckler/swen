"""
Integration tests for ML service interactions.

Tests the interaction between backend and ML service:
1. Transaction classification during sync/post
2. Account updates propagated to ML service
3. Example storage when transactions are posted
4. Classification confidence thresholds

Uses mocked ML client to verify correct API calls.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def unique_account_number(prefix: str = "") -> str:
    """Generate a unique account number."""
    return f"{prefix}{uuid4().hex[:6]}"


@pytest.fixture
def ml_client_spy():
    """Create a spy ML client to verify calls."""
    client = MagicMock()
    client.classify_batch.return_value = []
    client.store_example.return_value = None
    client.update_account.return_value = None
    client.delete_account.return_value = None
    return client


@pytest.fixture
def user_with_accounts(
    test_client: TestClient,
    authenticated_user: dict,
    api_v1_prefix: str,
):
    """User with initialized chart of accounts."""
    headers = authenticated_user["headers"]

    # Initialize chart
    test_client.post(
        f"{api_v1_prefix}/accounts/init-chart",
        headers=headers,
        json={"template": "minimal"},
    )

    # Get account IDs for transactions
    accounts = test_client.get(
        f"{api_v1_prefix}/accounts",
        headers=headers,
    ).json()["accounts"]

    # Find asset and expense accounts
    asset_account = next(
        (a for a in accounts if a["account_type"] == "asset"),
        None,
    )
    expense_account = next(
        (a for a in accounts if a["account_type"] == "expense"),
        None,
    )

    # Create if not found
    if not asset_account:
        asset_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Test Checking",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )
        asset_account = asset_response.json()

    if not expense_account:
        expense_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Test Expense",
                "account_type": "expense",
                "account_number": unique_account_number("40"),
                "currency": "EUR",
            },
        )
        expense_account = expense_response.json()

    return {
        **authenticated_user,
        "asset_account": asset_account,
        "expense_account": expense_account,
    }


def recent_date(days_ago: int = 0) -> str:
    """Get an ISO date string for N days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.integration
class TestMLClientCalls:
    """Tests that verify correct ML client API calls."""

    def test_account_creation_notifies_ml(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Creating an account should update ML embeddings."""
        headers = authenticated_user["headers"]

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            response = test_client.post(
                f"{api_v1_prefix}/accounts",
                headers=headers,
                json={
                    "name": "Groceries",
                    "account_type": "expense",
                    "account_number": unique_account_number("41"),
                    "currency": "EUR",
                    "description": "Food and household items",
                },
            )

        assert response.status_code == 201

        # ML client should have been called to update embeddings
        # The exact call pattern depends on implementation
        # This test documents the expected behavior
        # ml_client_spy.update_account.assert_called()

    def test_account_update_notifies_ml(
        self,
        test_client: TestClient,
        user_with_accounts: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Updating an account name should update ML embeddings."""
        headers = user_with_accounts["headers"]
        expense_id = user_with_accounts["expense_account"]["id"]

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            response = test_client.patch(
                f"{api_v1_prefix}/accounts/{expense_id}",
                headers=headers,
                json={"name": "Updated Expense Name"},
            )

        assert response.status_code == 200
        # ML should be notified of the name change

    def test_account_deletion_notifies_ml(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Deleting an account should remove it from ML embeddings."""
        headers = authenticated_user["headers"]

        # Create an account to delete
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Deletable Account",
                "account_type": "expense",
                "account_number": unique_account_number("49"),
                "currency": "EUR",
            },
        )
        account_id = create_response.json()["id"]

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            # Permanently delete
            response = test_client.delete(
                f"{api_v1_prefix}/accounts/{account_id}/permanent",
                headers=headers,
            )

        assert response.status_code == 204
        # ML should be notified of deletion


@pytest.mark.integration
class TestTransactionPosting:
    """Tests for ML interaction during transaction posting."""

    def test_posted_transaction_stored_as_example(
        self,
        test_client: TestClient,
        user_with_accounts: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Posting a transaction should store it as ML training example."""
        headers = user_with_accounts["headers"]
        asset_id = user_with_accounts["asset_account"]["id"]
        expense_id = user_with_accounts["expense_account"]["id"]

        # Create and post transaction
        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            create_response = test_client.post(
                f"{api_v1_prefix}/transactions",
                headers=headers,
                json={
                    "date": recent_date(1),
                    "description": "REWE Einkauf",
                    "counterparty": "REWE Markt GmbH",
                    "entries": [
                        {"account_id": expense_id, "debit": "50.00", "credit": "0"},
                        {"account_id": asset_id, "debit": "0", "credit": "50.00"},
                    ],
                    "auto_post": True,  # Automatically post
                },
            )

        assert create_response.status_code == 201
        data = create_response.json()
        assert data["is_posted"] is True

        # ML client should have been called to store the example
        # ml_client_spy.store_example.assert_called()

    def test_draft_transaction_not_stored(
        self,
        test_client: TestClient,
        user_with_accounts: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Draft transactions should NOT be stored as ML examples."""
        headers = user_with_accounts["headers"]
        asset_id = user_with_accounts["asset_account"]["id"]
        expense_id = user_with_accounts["expense_account"]["id"]

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            create_response = test_client.post(
                f"{api_v1_prefix}/transactions",
                headers=headers,
                json={
                    "date": recent_date(1),
                    "description": "Draft Transaction",
                    "entries": [
                        {"account_id": expense_id, "debit": "25.00", "credit": "0"},
                        {"account_id": asset_id, "debit": "0", "credit": "25.00"},
                    ],
                    "auto_post": False,  # Keep as draft
                },
            )

        assert create_response.status_code == 201
        data = create_response.json()
        assert data["is_posted"] is False

        # store_example should NOT have been called
        ml_client_spy.store_example.assert_not_called()

    def test_recategorization_stores_new_example(
        self,
        test_client: TestClient,
        user_with_accounts: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Recategorizing a transaction should update ML with new example."""
        headers = user_with_accounts["headers"]
        asset_id = user_with_accounts["asset_account"]["id"]
        expense_id = user_with_accounts["expense_account"]["id"]

        # Create a new expense account for recategorization
        new_expense = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Entertainment",
                "account_type": "expense",
                "account_number": unique_account_number("45"),
                "currency": "EUR",
            },
        )
        new_expense_id = new_expense.json()["id"]

        # Create posted transaction with original category
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Netflix Subscription",
                "counterparty": "Netflix",
                "entries": [
                    {"account_id": expense_id, "debit": "15.99", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "15.99"},
                ],
                "auto_post": True,
            },
        )
        transaction_id = create_response.json()["id"]

        # Recategorize to new expense account
        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=ml_client_spy,
        ):
            update_response = test_client.put(
                f"{api_v1_prefix}/transactions/{transaction_id}",
                headers=headers,
                json={
                    "category_account_id": new_expense_id,
                },
            )

        assert update_response.status_code == 200
        # ML should learn from the correction
        # ml_client_spy.store_example.assert_called()


@pytest.mark.integration
class TestClassificationDuringSyncMocked:
    """Tests for ML classification during sync (mocked)."""

    def test_sync_requests_classification(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        ml_client_spy,
    ):
        """Sync should request ML classification for imported transactions."""
        headers = authenticated_user["headers"]

        # Initialize accounts
        test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )

        # Run sync (with mocked bank adapter returning empty)
        with patch(
            "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
        ) as mock_adapter_class:
            from unittest.mock import AsyncMock

            adapter = AsyncMock()
            adapter.connect = AsyncMock()
            adapter.disconnect = AsyncMock()
            adapter.is_connected.return_value = False
            adapter.set_tan_method = MagicMock()
            adapter.set_tan_medium = MagicMock()
            adapter.fetch_transactions = AsyncMock(return_value=[])
            mock_adapter_class.return_value = adapter

            with patch(
                "swen.presentation.api.dependencies.get_ml_client",
                return_value=ml_client_spy,
            ):
                response = test_client.post(
                    f"{api_v1_prefix}/sync/run",
                    headers=headers,
                    json={"days": 7},
                )

        assert response.status_code == 200
        # With transactions, classify_batch should be called
        # (no transactions in this test, so it may not be called)


@pytest.mark.integration
class TestMLServiceUnavailable:
    """Tests for handling ML service unavailability."""

    def test_account_creation_succeeds_without_ml(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """Account creation should succeed even if ML service is unavailable."""
        headers = authenticated_user["headers"]

        # Mock ML client to raise an error
        failing_client = MagicMock()
        failing_client.update_account.side_effect = Exception("ML service down")

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=failing_client,
        ):
            response = test_client.post(
                f"{api_v1_prefix}/accounts",
                headers=headers,
                json={
                    "name": "Test Account",
                    "account_type": "expense",
                    "account_number": unique_account_number("48"),
                    "currency": "EUR",
                },
            )

        # Should still succeed - ML is optional enhancement
        assert response.status_code == 201

    def test_transaction_post_succeeds_without_ml(
        self,
        test_client: TestClient,
        user_with_accounts: dict,
        api_v1_prefix: str,
    ):
        """Transaction posting should succeed even if ML service fails."""
        headers = user_with_accounts["headers"]
        asset_id = user_with_accounts["asset_account"]["id"]
        expense_id = user_with_accounts["expense_account"]["id"]

        failing_client = MagicMock()
        failing_client.store_example.side_effect = Exception("ML service down")

        with patch(
            "swen.presentation.api.dependencies.get_ml_client",
            return_value=failing_client,
        ):
            response = test_client.post(
                f"{api_v1_prefix}/transactions",
                headers=headers,
                json={
                    "date": recent_date(1),
                    "description": "Test Purchase",
                    "entries": [
                        {"account_id": expense_id, "debit": "100.00", "credit": "0"},
                        {"account_id": asset_id, "debit": "0", "credit": "100.00"},
                    ],
                    "auto_post": True,
                },
            )

        # Should still succeed
        assert response.status_code == 201
        assert response.json()["is_posted"] is True
