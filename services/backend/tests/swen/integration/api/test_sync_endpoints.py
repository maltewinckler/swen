"""Integration tests for sync endpoints."""

from fastapi.testclient import TestClient

from tests.shared.sse import get_sse_event, read_sse_events


class TestRunSyncStreaming:
    """Tests for POST /api/v1/sync/run/stream."""

    def test_run_sync_stream_no_accounts(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Run streaming sync with no mapped accounts returns summary events."""
        with test_client.stream(
            "POST",
            f"{api_v1_prefix}/sync/run/stream",
            headers=auth_headers,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            events = read_sse_events(response)

        assert [event_type for event_type, _ in events] == [
            "batch_sync_started",
            "batch_sync_completed",
            "result",
        ]

        started_event = events[0][1]
        completed_event = events[1][1]
        result_event = get_sse_event(events, "result")

        assert started_event["total_accounts"] == 0
        assert completed_event["accounts_synced"] == 0
        assert completed_event["total_imported"] == 0
        assert result_event["success"] is True
        assert result_event["total_imported"] == 0
        assert result_event["total_skipped"] == 0
        assert result_event["total_failed"] == 0
        assert result_event["accounts_synced"] == 0

    def test_run_sync_stream_with_params(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Streaming sync accepts explicit request parameters."""
        with test_client.stream(
            "POST",
            f"{api_v1_prefix}/sync/run/stream",
            headers=auth_headers,
            json={"days": 30, "auto_post": False},
        ) as response:
            assert response.status_code == 200
            events = read_sse_events(response)

        result_event = get_sse_event(events, "result")
        assert result_event["success"] is True
        assert result_event["accounts_synced"] == 0

    def test_run_sync_stream_with_iban_filter(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Streaming sync respects an IBAN filter with no matches."""
        with test_client.stream(
            "POST",
            f"{api_v1_prefix}/sync/run/stream",
            headers=auth_headers,
            json={"days": 30, "iban": "DE89370400440532013000"},
        ) as response:
            assert response.status_code == 200
            events = read_sse_events(response)

        result_event = get_sse_event(events, "result")
        assert result_event["accounts_synced"] == 0

    def test_run_sync_stream_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot run streaming sync without auth."""
        with test_client.stream("POST", f"{api_v1_prefix}/sync/run/stream") as response:
            assert response.status_code == 401


class TestSyncStatus:
    """Tests for GET /api/v1/sync/status."""

    def test_get_sync_status_empty(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Get sync status for new user with no syncs."""
        response = test_client.get(
            f"{api_v1_prefix}/sync/status",
            headers=auth_headers,
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
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot get sync status without auth."""
        response = test_client.get(f"{api_v1_prefix}/sync/status")
        assert response.status_code == 401
