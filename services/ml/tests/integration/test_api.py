"""Integration tests for API endpoints."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, test_client: TestClient) -> None:
        """Test health check returns OK."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert "distiluse" in data["model_name"]


class TestClassifyEndpoint:
    """Tests for /classify endpoint."""

    def test_classify_without_examples(self, test_client: TestClient) -> None:
        """Test classification with no prior examples."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        response = test_client.post(
            "/classify",
            json={
                "user_id": user_id,
                "transaction": {
                    "purpose": "REWE SAGT DANKE 12345",
                    "amount": "-45.67",
                    "counterparty_name": "REWE",
                    "booking_date": "2026-01-15",
                },
                "available_accounts": [
                    {
                        "account_id": account_id,
                        "account_number": "4200",
                        "name": "Lebensmittel",
                        "account_type": "expense",
                        "description": "Supermarkets: REWE, Lidl, EDEKA",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "similarity_score" in data
        assert "confidence" in data
        assert data["inference_time_ms"] >= 0

    def test_classify_with_example(self, test_client: TestClient) -> None:
        """Test that adding an example improves classification."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        # First, add an example
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "purpose": "REWE MARKT BERLIN",
                "amount": "-32.50",
                "counterparty_name": "REWE",
            },
        )

        # Also embed the account description
        test_client.post(
            "/accounts/embed",
            json={
                "user_id": user_id,
                "accounts": [
                    {
                        "account_id": account_id,
                        "account_number": "4200",
                        "name": "Lebensmittel",
                        "account_type": "expense",
                        "description": "Supermarkets",
                    }
                ],
            },
        )

        # Now classify a similar transaction
        response = test_client.post(
            "/classify",
            json={
                "user_id": user_id,
                "transaction": {
                    "purpose": "REWE SAGT DANKE HAMBURG",
                    "amount": "-45.67",
                    "counterparty_name": "REWE",
                    "booking_date": "2026-01-15",
                },
                "available_accounts": [
                    {
                        "account_id": account_id,
                        "account_number": "4200",
                        "name": "Lebensmittel",
                        "account_type": "expense",
                        "description": "Supermarkets",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should match with reasonable similarity (amount differences affect score)
        assert data["similarity_score"] > 0.5
        assert data["match_type"] == "example"


class TestExamplesEndpoint:
    """Tests for /examples endpoint."""

    def test_add_example(self, test_client: TestClient) -> None:
        """Test adding an example."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        response = test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "purpose": "REWE SAGT DANKE 12345",
                "amount": "-45.67",
                "counterparty_name": "REWE",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stored"] is True
        assert data["total_examples"] == 1
        assert data["constructed_text"] is not None


class TestAccountsEndpoint:
    """Tests for /accounts endpoint."""

    def test_embed_accounts(self, test_client: TestClient) -> None:
        """Test embedding account descriptions."""
        user_id = str(uuid4())

        response = test_client.post(
            "/accounts/embed",
            json={
                "user_id": user_id,
                "accounts": [
                    {
                        "account_id": str(uuid4()),
                        "account_number": "4200",
                        "name": "Lebensmittel",
                        "account_type": "expense",
                        "description": "Supermarkets: REWE, Lidl",
                    },
                    {
                        "account_id": str(uuid4()),
                        "account_number": "4300",
                        "name": "Transport",
                        "account_type": "expense",
                        "description": None,  # No description - will use name only
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All accounts are embedded - those without description use name only
        assert data["embedded"] == 2

    def test_delete_account(self, test_client: TestClient) -> None:
        """Test deleting account embeddings."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        # Add an example first
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "purpose": "Test",
                "amount": "-10.00",
            },
        )

        # Delete
        response = test_client.delete(f"/accounts/{user_id}/{account_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["examples_deleted"] == 1


class TestUsersEndpoint:
    """Tests for /users endpoint."""

    def test_get_user_stats(self, test_client: TestClient) -> None:
        """Test getting user statistics."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        # Add some examples
        for i in range(3):
            test_client.post(
                "/examples",
                json={
                    "user_id": user_id,
                    "account_id": account_id,
                    "purpose": f"Test {i}",
                    "amount": "-10.00",
                },
            )

        response = test_client.get(f"/users/{user_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_examples"] == 3
        assert data["accounts_with_examples"] == 1

    def test_delete_user(self, test_client: TestClient) -> None:
        """Test deleting all user data."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        # Add some data
        test_client.post(
            "/accounts/embed",
            json={
                "user_id": user_id,
                "accounts": [
                    {
                        "account_id": account_id,
                        "account_number": "4200",
                        "name": "Test",
                        "account_type": "expense",
                        "description": "Test account",
                    }
                ],
            },
        )
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "purpose": "Test",
                "amount": "-10.00",
            },
        )

        # Delete user
        response = test_client.delete(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["accounts_deleted"] == 1
        assert data["examples_deleted"] == 1

        # Verify user has no stats now
        stats_response = test_client.get(f"/users/{user_id}/stats")
        stats = stats_response.json()
        assert stats["total_examples"] == 0
