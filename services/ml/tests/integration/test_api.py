"""Integration tests for API endpoints."""

from uuid import uuid4

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
        assert "bge-m3" in data["model_name"].lower()


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
        transaction_id = str(uuid4())

        # First, add an example
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
                "purpose": "REWE MARKT BERLIN",
                "amount": "-32.50",
                "counterparty_name": "REWE",
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


class TestExamplesEndpoint:
    """Tests for /examples endpoint."""

    def test_add_example(self, test_client: TestClient) -> None:
        """Test adding an example."""
        user_id = str(uuid4())
        account_id = str(uuid4())
        transaction_id = str(uuid4())

        response = test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
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

    def test_add_duplicate_example_skipped(self, test_client: TestClient) -> None:
        """Test that duplicate transaction_id is skipped."""
        user_id = str(uuid4())
        account_id = str(uuid4())
        transaction_id = str(uuid4())

        # Add first example
        response1 = test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
                "purpose": "REWE MARKT",
                "amount": "-30.00",
            },
        )
        assert response1.status_code == 200
        assert response1.json()["stored"] is True

        # Try to add same transaction_id again
        response2 = test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
                "purpose": "REWE MARKT DIFFERENT",
                "amount": "-50.00",
            },
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["stored"] is False
        assert data["total_examples"] == 1  # Still only 1


class TestAccountsEndpoint:
    """Tests for /accounts endpoint."""

    def test_delete_account(self, test_client: TestClient) -> None:
        """Test deleting account embeddings."""
        user_id = str(uuid4())
        account_id = str(uuid4())
        transaction_id = str(uuid4())

        # Add an example first
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
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

        # Add some examples with unique transaction_ids
        for i in range(3):
            test_client.post(
                "/examples",
                json={
                    "user_id": user_id,
                    "account_id": account_id,
                    "transaction_id": str(uuid4()),
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
        transaction_id = str(uuid4())

        # Add some data via examples
        test_client.post(
            "/examples",
            json={
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
                "purpose": "Test",
                "amount": "-10.00",
            },
        )

        # Delete user
        response = test_client.delete(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["accounts_deleted"] == 1  # 1 account with examples
        assert data["examples_deleted"] == 1

        # Verify user has no stats now
        stats_response = test_client.get(f"/users/{user_id}/stats")
        stats = stats_response.json()
        assert stats["total_examples"] == 0
