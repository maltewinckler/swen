"""Integration tests for sync endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestRunSync:
    """Tests for POST /api/v1/sync/run."""

    def test_run_sync_no_accounts(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Run sync with no mapped accounts returns empty result."""
        response = test_client.post(
            f"{api_v1_prefix}/sync/run", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return successful but empty result
        assert data["success"] is True
        assert data["total_fetched"] == 0
        assert data["total_imported"] == 0
        assert data["accounts_synced"] == 0
        assert data["account_stats"] == []

    def test_run_sync_with_params(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Run sync with custom parameters."""
        response = test_client.post(
            f"{api_v1_prefix}/sync/run",
            headers=auth_headers,
            json={
                "days": 30,
                "auto_post": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["auto_post"] is False
        assert "synced_at" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_run_sync_with_iban_filter(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Run sync with IBAN filter (no matching account)."""
        response = test_client.post(
            f"{api_v1_prefix}/sync/run",
            headers=auth_headers,
            json={
                "days": 30,
                "iban": "DE89370400440532013000",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty since no accounts match
        assert data["accounts_synced"] == 0

    def test_run_sync_unauthorized(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot run sync without auth."""
        response = test_client.post(f"{api_v1_prefix}/sync/run")
        assert response.status_code == 401


class TestSyncStatus:
    """Tests for GET /api/v1/sync/status."""

    def test_get_sync_status_empty(
        self, test_client: TestClient, auth_headers: dict, api_v1_prefix: str
    ):
        """Get sync status for new user with no syncs."""
        response = test_client.get(
            f"{api_v1_prefix}/sync/status", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success_count"] == 0
        assert data["failed_count"] == 0
        assert data["pending_count"] == 0
        assert data["duplicate_count"] == 0
        assert data["skipped_count"] == 0
        assert data["total_count"] == 0

    def test_get_sync_status_unauthorized(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Cannot get sync status without auth."""
        response = test_client.get(f"{api_v1_prefix}/sync/status")
        assert response.status_code == 401
