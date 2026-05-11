"""Integration tests for credentials endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from swen.domain.banking.value_objects.bank_info import BankInfo

MOCK_BANK_INFO = BankInfo(
    blz="12345678",
    name="Test Bank",
    bic="TESTDE00XXX",
    organization=None,
    is_fints_capable=True,
)


class TestListCredentials:
    """Tests for GET /api/v1/bank-connections/credentials."""

    def test_list_credentials_empty(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """List credentials returns empty for new user."""
        response = test_client.get(
            f"{api_v1_prefix}/bank-connections/credentials",
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
        response = test_client.get(f"{api_v1_prefix}/bank-connections/credentials")
        assert response.status_code == 401


class TestStoreCredentials:
    """Tests for POST /api/v1/bank-connections/credentials."""

    def test_store_credentials_success(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully store bank credentials without tan_method returns 204."""
        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
            },
        )

        assert response.status_code == 204
        assert response.content == b""

    def test_store_credentials_with_tan_method(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully store bank credentials including tan_method returns 204."""
        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": "33333333",
                "username": "testuser",
                "pin": "testpin123",
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        )

        assert response.status_code == 204
        assert response.content == b""

    def test_store_credentials_duplicate(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Cannot store duplicate credentials for same bank."""
        duplicate_test_blz = "11111111"

        # Store first
        first_response = test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": duplicate_test_blz,
                "username": "testuser",
                "pin": "testpin123",
            },
        )
        assert first_response.status_code == 204, (
            f"First store failed: {first_response.text}"
        )

        # Try to store again
        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": duplicate_test_blz,
                "username": "testuser2",
                "pin": "testpin456",
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
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": "123",  # Too short
                "username": "testuser",
                "pin": "testpin123",
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
            f"{api_v1_prefix}/bank-connections/credentials",
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
            },
        )
        assert response.status_code == 401


class TestDeleteCredentials:
    """Tests for DELETE /api/v1/bank-connections/credentials/{blz}."""

    def test_delete_credentials_success(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully delete stored credentials."""
        # Store first
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin123",
            },
        )

        # Delete
        response = test_client.delete(
            f"{api_v1_prefix}/bank-connections/credentials/12345678",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deleted
        list_response = test_client.get(
            f"{api_v1_prefix}/bank-connections/credentials",
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
            f"{api_v1_prefix}/bank-connections/credentials/12345678",
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
            f"{api_v1_prefix}/bank-connections/credentials/123",
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
        response = test_client.delete(
            f"{api_v1_prefix}/bank-connections/credentials/12345678"
        )
        assert response.status_code == 401


class TestLookupBank:
    """Tests for GET /api/v1/bank-connections/lookup/{blz}."""

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    def test_lookup_bank_success(
        self,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully lookup bank info."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        response = test_client.get(
            f"{api_v1_prefix}/bank-connections/lookup/12345678",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["blz"] == "12345678"
        assert data["name"] == "Test Bank"
        assert data["is_fints_capable"] is True

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    def test_lookup_bank_not_found(
        self,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Lookup unknown bank returns 404."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = None
        mock_lookup_factory.return_value = mock_query

        response = test_client.get(
            f"{api_v1_prefix}/bank-connections/lookup/99999999",
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
            f"{api_v1_prefix}/bank-connections/lookup/123",
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestQueryTanMethods:
    """Tests for POST /api/v1/bank-connections/tan-methods.

    Credentials must be stored first; the endpoint reads them from DB.
    """

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    @patch(
        "swen.application.queries.banking.query_tan_methods_query.BankConnectionDispatcher"
    )
    def test_query_tan_methods_success(
        self,
        mock_adapter_class,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully query TAN methods from bank when credentials are stored."""
        from swen.domain.banking.value_objects import TANMethod, TANMethodType

        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        # Mock the adapter instance
        mock_adapter = MagicMock()
        mock_adapter_class.from_factory.return_value = mock_adapter

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

        # Store credentials first
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={
                "blz": "12345678",
                "username": "testuser",
                "pin": "testpin",
            },
        )

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "12345678"},
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
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    def test_query_tan_methods_bank_not_found(
        self,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods fails for unknown bank."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = None
        mock_lookup_factory.return_value = mock_query

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "99999999"},
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
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "123"},  # Too short
        )

        assert response.status_code == 422  # Pydantic validation

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    def test_query_tan_methods_credentials_not_found(
        self,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods returns 404 when no credentials are stored for the BLZ."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "77777777"},
        )

        assert response.status_code == 404
        assert "credentials" in response.json()["detail"].lower()

    def test_query_tan_methods_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot query TAN methods without auth."""
        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            json={"blz": "12345678"},
        )

        assert response.status_code == 401

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    @patch(
        "swen.application.queries.banking.query_tan_methods_query.BankConnectionDispatcher"
    )
    def test_query_tan_methods_connection_failure(
        self,
        mock_adapter_class,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods returns 503 on connection failure."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        mock_adapter = MagicMock()
        mock_adapter_class.from_factory.return_value = mock_adapter

        async def mock_get_tan_methods_failure(credentials):
            raise Exception("Connection timeout")

        mock_adapter.get_tan_methods = mock_get_tan_methods_failure

        # Store credentials so the query proceeds past the 404 check
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={"blz": "12345678", "username": "u", "pin": "p"},
        )

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "12345678"},
        )

        assert response.status_code == 503
        assert "Failed to connect to bank" in response.json()["detail"]

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    @patch(
        "swen.application.queries.banking.query_tan_methods_query.BankConnectionDispatcher"
    )
    def test_query_tan_methods_invalid_credentials(
        self,
        mock_adapter_class,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods returns 401 on invalid credentials."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        mock_adapter = MagicMock()
        mock_adapter_class.from_factory.return_value = mock_adapter

        async def mock_get_tan_methods_auth_error(credentials):
            raise Exception("Authentication failed: invalid PIN")

        mock_adapter.get_tan_methods = mock_get_tan_methods_auth_error

        # Store credentials so the query proceeds past the 404 check
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={"blz": "12345678", "username": "u", "pin": "wrongpin"},
        )

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "12345678"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @patch(
        "swen.application.queries.banking.lookup_bank_query.LookupBankQuery.from_factory",
    )
    @patch(
        "swen.application.queries.banking.query_tan_methods_query.BankConnectionDispatcher"
    )
    def test_query_tan_methods_empty_result(
        self,
        mock_adapter_class,
        mock_lookup_factory,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Query TAN methods handles empty result from bank."""
        mock_query = AsyncMock()
        mock_query.execute.return_value = MOCK_BANK_INFO
        mock_lookup_factory.return_value = mock_query

        mock_adapter = MagicMock()
        mock_adapter_class.from_factory.return_value = mock_adapter

        async def mock_get_tan_methods_empty(credentials):
            return []

        mock_adapter.get_tan_methods = mock_get_tan_methods_empty

        # Store credentials so the query proceeds past the 404 check
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={"blz": "12345678", "username": "u", "pin": "p"},
        )

        response = test_client.post(
            f"{api_v1_prefix}/bank-connections/tan-methods",
            headers=auth_headers,
            json={"blz": "12345678"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tan_methods"] == []
        assert data["default_method"] is None


class TestUpdateCredentialsTan:
    """Tests for PATCH /api/v1/bank-connections/credentials/{blz}."""

    def test_update_tan_settings_success(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Successfully update TAN settings for stored credentials."""
        # Store first
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={"blz": "12345678", "username": "u", "pin": "p"},
        )

        response = test_client.patch(
            f"{api_v1_prefix}/bank-connections/credentials/12345678",
            headers=auth_headers,
            json={"tan_method": "946", "tan_medium": "SecureGo"},
        )

        assert response.status_code == 204

    def test_update_tan_settings_not_found(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Returns 404 when no credentials exist for the BLZ."""
        response = test_client.patch(
            f"{api_v1_prefix}/bank-connections/credentials/88888888",
            headers=auth_headers,
            json={"tan_method": "946", "tan_medium": None},
        )

        assert response.status_code == 404

    def test_update_tan_settings_invalid_blz(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Returns 400 for invalid BLZ format."""
        response = test_client.patch(
            f"{api_v1_prefix}/bank-connections/credentials/123",
            headers=auth_headers,
            json={"tan_method": "946", "tan_medium": None},
        )

        assert response.status_code == 400
        assert "8 digits" in response.json()["detail"]

    def test_update_tan_settings_unauthorized(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Cannot update credentials without auth."""
        response = test_client.patch(
            f"{api_v1_prefix}/bank-connections/credentials/12345678",
            json={"tan_method": "946", "tan_medium": None},
        )

        assert response.status_code == 401

    def test_update_tan_settings_null_method(
        self,
        test_client: TestClient,
        auth_headers: dict,
        api_v1_prefix: str,
    ):
        """Allows setting tan_method to null (clears TAN settings)."""
        # Store first
        test_client.post(
            f"{api_v1_prefix}/bank-connections/credentials",
            headers=auth_headers,
            json={"blz": "12345678", "username": "u", "pin": "p"},
        )

        response = test_client.patch(
            f"{api_v1_prefix}/bank-connections/credentials/12345678",
            headers=auth_headers,
            json={"tan_method": None, "tan_medium": None},
        )

        assert response.status_code == 204
