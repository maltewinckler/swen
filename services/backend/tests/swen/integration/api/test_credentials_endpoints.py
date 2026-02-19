"""Integration tests for credentials endpoints."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@dataclass
class MockInstituteInfo:
    """Mock FinTS institute info for tests."""

    blz: str
    name: str
    bic: str
    city: str
    endpoint_url: str


# Mock FinTS institute info for tests
MOCK_INSTITUTE_INFO = MockInstituteInfo(
    blz="12345678",
    name="Test Bank",
    bic="TESTDE00XXX",
    city="Berlin",
    endpoint_url="https://banking.test.de/fints",
)


class TestListCredentials:
    """Tests for GET /api/v1/credentials."""

    def test_list_credentials_empty(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """List credentials returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["credentials"] == []
        assert data["total"] == 0

    def test_list_credentials_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot list credentials without auth."""
        response = test_client.get(f"{api_v1_prefix}/credentials")
        assert response.status_code == 401


class TestStoreCredentials:
    """Tests for POST /api/v1/credentials."""

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_store_credentials_success(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully store bank credentials."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["blz"] == "12345678"
        assert data["label"] == "Test Bank"
        assert "credential_id" in data
        assert data["message"] == "Credentials stored successfully"

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_store_credentials_bank_not_found(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot store credentials for unknown bank."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = None
        mock_directory.return_value = mock_dir

        response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": "99999999",
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_store_credentials_duplicate(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot store duplicate credentials for same bank."""
        # Use a unique BLZ to avoid conflicts with other tests
        duplicate_test_blz = "11111111"
        duplicate_institute = MockInstituteInfo(
            blz=duplicate_test_blz,
            name="Duplicate Test Bank",
            bic="DUPTDE00XXX",
            city="Munich",
            endpoint_url="https://banking.duplicate.de/fints",
        )
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = duplicate_institute
        mock_directory.return_value = mock_dir

        # Store first
        first_response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": duplicate_test_blz,
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )
        assert first_response.status_code == 201, (
            f"First store failed: {first_response.json()}"
        )

        # Try to store again
        response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": duplicate_test_blz,
                "username": "testuser2",
                "pin": "testpin456",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    def test_store_credentials_invalid_blz(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot store credentials with invalid BLZ format."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": "123",  # Too short
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        assert response.status_code == 422  # Pydantic validation

    def test_store_credentials_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot store credentials without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials",
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )
        assert response.status_code == 401


class TestDeleteCredentials:
    """Tests for DELETE /api/v1/credentials/{blz}."""

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_delete_credentials_success(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully delete stored credentials."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        # Store first
        test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        # Delete
        response = test_client.delete(
            f"{api_v1_prefix}/credentials/12345678",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted
        list_response = test_client.get(
            f"{api_v1_prefix}/credentials",
            headers=auth_headers,
        )
        assert list_response.json()["total"] == 0

    def test_delete_credentials_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot delete non-existent credentials."""
        response = test_client.delete(
            f"{api_v1_prefix}/credentials/12345678",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_credentials_invalid_blz(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot delete with invalid BLZ format."""
        response = test_client.delete(
            f"{api_v1_prefix}/credentials/123",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "8 digits" in response.json()["detail"]

    def test_delete_credentials_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot delete credentials without auth."""
        response = test_client.delete(f"{api_v1_prefix}/credentials/12345678")
        assert response.status_code == 401


class TestLookupBank:
    """Tests for GET /api/v1/credentials/lookup/{blz}."""

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_lookup_bank_success(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully lookup bank info."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        response = test_client.get(
            f"{api_v1_prefix}/credentials/lookup/12345678",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["blz"] == "12345678"
        assert data["name"] == "Test Bank"
        assert data["endpoint_url"] == "https://banking.test.de/fints"

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_lookup_bank_not_found(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Lookup unknown bank returns 404."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = None
        mock_directory.return_value = mock_dir

        response = test_client.get(
            f"{api_v1_prefix}/credentials/lookup/99999999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_lookup_bank_invalid_blz(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Lookup with invalid BLZ format returns 400."""
        response = test_client.get(
            f"{api_v1_prefix}/credentials/lookup/123",
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestQueryTanMethods:
    """Tests for POST /api/v1/credentials/tan-methods."""

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    @patch("swen.application.queries.banking.query_tan_methods_query.GeldstromAdapter")
    def test_query_tan_methods_success(
        self,
        mock_adapter_class,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully query TAN methods from bank."""
        from swen.domain.banking.value_objects import TANMethod, TANMethodType

        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        # Mock the adapter instance
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        # Create async mock for get_tan_methods
        async def mock_get_tan_methods(credentials):
            return [
                TANMethod(
                    code="940",
                    name="DKB App",
                    method_type=TANMethodType.DECOUPLED,
                    is_decoupled=True,
                    technical_id="SealOne",
                    decoupled_max_polls=999,
                    decoupled_first_poll_delay=5,
                    decoupled_poll_interval=2,
                ),
                TANMethod(
                    code="972",
                    name="chipTAN optical",
                    method_type=TANMethodType.CHIPTAN,
                    is_decoupled=False,
                ),
            ]

        mock_adapter.get_tan_methods = mock_get_tan_methods

        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["blz"] == "12345678"
        assert data["bank_name"] == "Test Bank"
        assert len(data["tan_methods"]) == 2
        assert data["default_method"] == "940"  # First decoupled method

        # Verify first method details
        method1 = data["tan_methods"][0]
        assert method1["code"] == "940"
        assert method1["name"] == "DKB App"
        assert method1["method_type"] == "decoupled"
        assert method1["is_decoupled"] is True

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    def test_query_tan_methods_bank_not_found(
        self,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods fails for unknown bank."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = None
        mock_directory.return_value = mock_dir

        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "99999999",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_query_tan_methods_invalid_blz(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods fails with invalid BLZ format."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "123",  # Too short
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 422  # Pydantic validation

    def test_query_tan_methods_missing_username(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods fails without username."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "pin": "testpin",
            },
        )

        assert response.status_code == 422  # Pydantic validation

    def test_query_tan_methods_missing_pin(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods fails without PIN."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
            },
        )

        assert response.status_code == 422  # Pydantic validation

    def test_query_tan_methods_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot query TAN methods without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 401

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    @patch("swen.application.queries.banking.query_tan_methods_query.GeldstromAdapter")
    def test_query_tan_methods_connection_failure(
        self,
        mock_adapter_class,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods returns 503 on connection failure."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        async def mock_get_tan_methods_failure(credentials):
            raise Exception("Connection timeout")

        mock_adapter.get_tan_methods = mock_get_tan_methods_failure

        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 503
        assert "Failed to connect to bank" in response.json()["detail"]

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    @patch("swen.application.queries.banking.query_tan_methods_query.GeldstromAdapter")
    def test_query_tan_methods_invalid_credentials(
        self,
        mock_adapter_class,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods returns 401 on invalid credentials."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        async def mock_get_tan_methods_auth_error(credentials):
            raise Exception("Authentication failed: invalid PIN")

        mock_adapter.get_tan_methods = mock_get_tan_methods_auth_error

        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "wrongpin",
            },
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    )
    @patch("swen.application.queries.banking.query_tan_methods_query.GeldstromAdapter")
    def test_query_tan_methods_empty_result(
        self,
        mock_adapter_class,
        mock_directory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods handles empty result from bank."""
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE_INFO
        mock_directory.return_value = mock_dir

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        async def mock_get_tan_methods_empty(credentials):
            return []

        mock_adapter.get_tan_methods = mock_get_tan_methods_empty

        response = test_client.post(
            f"{api_v1_prefix}/credentials/tan-methods",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tan_methods"] == []
        assert data["default_method"] is None
