"""Integration tests for admin local FinTS configuration endpoints."""

import io

from fastapi.testclient import TestClient


# Minimal valid CSV matching the expected FinTS institute directory format.
# Must be CP1252-encoded (compatible with UTF-8 for ASCII chars).
# 27 columns: BLZ at index 1, PIN/TAN URL at index 24.
def _build_csv_row(fields: dict[int, str], num_cols: int = 27) -> str:
    """Build a semicolon-separated row with values at specific column indices."""
    cols = [""] * num_cols
    for idx, val in fields.items():
        cols[idx] = val
    return ";".join(cols)


VALID_CSV_HEADER = _build_csv_row(
    {
        0: "Nr.",
        1: "BLZ",
        2: "BIC",
        3: "Institut",
        4: "Ort",
        5: "RZ",
        6: "Organisation",
        7: "HBCI-Zugang DNS",
        8: "HBCI- Zugang IP-Adresse",
        9: "HBCI-Version",
        10: "DDV",
        11: "RDH-1",
        12: "RDH-2",
        13: "RDH-3",
        14: "RDH-4",
        15: "RDH-5",
        16: "RDH-6",
        17: "RDH-7",
        18: "RDH-8",
        19: "RDH-9",
        20: "RDH-10",
        21: "RAH-7",
        22: "RAH-9",
        23: "RAH-10",
        24: "PIN/TAN-Zugang URL",
        25: "Version",
        26: "Datum letzte Aenderung",
    }
)

VALID_CSV_ROW_1 = _build_csv_row(
    {
        0: "2",
        1: "10010010",
        2: "PBNKDEFFXXX",
        3: "Postbank",
        4: "Berlin",
        5: "eigenes Rechenzentrum",
        6: "BdB",
        24: "https://hbci.postbank.de/banking/hbci.do",
        25: "FinTS V3.0",
        26: "04.02.2022",
    }
)

VALID_CSV_ROW_2 = _build_csv_row(
    {
        0: "3",
        1: "10020200",
        2: "BHFBDEFFXXX",
        3: "BHF-Bank AG",
        4: "Berlin",
        5: "Bank-Verlag GmbH",
        6: "BdB",
        9: "3.0",
        11: "ja",
        13: "ja",
        15: "ja",
        24: "https://www.bv-activebanking.de/hbci",
        25: "FinTS V3.0",
    }
)

VALID_CSV = f"{VALID_CSV_HEADER}\n{VALID_CSV_ROW_1}\n{VALID_CSV_ROW_2}\n"

VALID_PRODUCT_ID = "1234567890A"


def _register_admin(test_client: TestClient, api_v1_prefix: str) -> str:
    """Register first user (becomes admin) and return access token."""
    response = test_client.post(
        f"{api_v1_prefix}/auth/register",
        json={"email": "admin@example.com", "password": "SecurePassword123!"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _create_regular_user(
    test_client: TestClient,
    api_v1_prefix: str,
    admin_token: str,
) -> str:
    """Create a non-admin user and return their access token."""
    test_client.post(
        f"{api_v1_prefix}/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "user@example.com", "password": "SecurePassword123!"},
    )
    login_response = test_client.post(
        f"{api_v1_prefix}/auth/login",
        json={"email": "user@example.com", "password": "SecurePassword123!"},
    )
    return login_response.json()["access_token"]


def _make_csv_upload(content: str = VALID_CSV) -> dict:
    """Build the files dict for CSV upload."""
    return {
        "file": (
            "fints_institute.csv",
            io.BytesIO(content.encode("cp1252")),
            "text/csv",
        )
    }


def _setup_initial_config(
    test_client: TestClient,
    api_v1_prefix: str,
    admin_token: str,
) -> None:
    """Create initial local FinTS config via POST /local_fints_configuration."""
    response = test_client.post(
        f"{api_v1_prefix}/admin/local_fints_configuration",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"product_id": VALID_PRODUCT_ID},
        files=_make_csv_upload(),
    )
    assert response.status_code == 200, f"Initial config failed: {response.text}"


# =============================================================================
# GET /admin/local_fints_configuration
# =============================================================================


class TestGetFinTSConfiguration:
    """Tests for GET /api/v1/admin/local_fints_configuration."""

    def test_returns_404_when_not_configured(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Should return 404 when no FinTS configuration exists."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_returns_configuration_after_setup(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Should return configuration after initial setup."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}

        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "product_id_masked" in data
        assert data["csv_institute_count"] == 2
        assert data["csv_file_size_kb"] >= 0
        assert "last_updated" in data
        assert "last_updated_by" in data

    def test_non_admin_cannot_access(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Non-admin users should get 403."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        user_token = _create_regular_user(test_client, api_v1_prefix, admin_token)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_unauthenticated_cannot_access(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Unauthenticated requests should get 401."""
        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration",
        )

        assert response.status_code == 401


# =============================================================================
# GET /admin/local_fints_configuration/status
# =============================================================================


class TestGetConfigurationStatus:
    """Tests for GET /api/v1/admin/local_fints_configuration/status."""

    def test_not_configured_initially(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Should report not configured when nothing is set up."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_configured"] is False

    def test_configured_after_initial_setup(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Should report configured after initial setup."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}

        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration/status",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_configured"] is True

    def test_non_admin_cannot_check_status(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Non-admin users should get 403."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        user_token = _create_regular_user(test_client, api_v1_prefix, admin_token)

        response = test_client.get(
            f"{api_v1_prefix}/admin/local_fints_configuration/status",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403


# =============================================================================
# POST /admin/local_fints_configuration
# =============================================================================


class TestUpsertLocalFinTSConfiguration:
    """Tests for POST /api/v1/admin/local_fints_configuration."""

    def test_first_time_setup_both_fields(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Admin can create initial configuration with product_id + CSV."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={"product_id": VALID_PRODUCT_ID},
            files=_make_csv_upload(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["institute_count"] == 2
        assert data["file_size_kb"] >= 0
        assert "message" in data

    def test_idempotent_upsert_both_fields(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Posting again with both fields is accepted (upsert, not 409)."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}

        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers=headers,
            data={"product_id": "AnotherProductID1"},
            files=_make_csv_upload(),
        )

        assert response.status_code == 200

    def test_partial_update_product_id_only(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Admin can update only the product_id when config already exists."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}

        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers=headers,
            data={"product_id": "NewProductID999"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["institute_count"] is None

    def test_partial_update_csv_only(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Admin can update only the CSV when config already exists."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}

        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers=headers,
            files=_make_csv_upload(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["institute_count"] == 2

    def test_no_fields_provided_rejected(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Posting with neither product_id nor file should return 400."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400

    def test_first_time_product_id_only_rejected(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """First-time setup requires both fields — product_id alone is rejected."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={"product_id": VALID_PRODUCT_ID},
        )

        assert response.status_code == 400

    def test_invalid_csv_rejected(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Invalid CSV content should be rejected."""
        admin_token = _register_admin(test_client, api_v1_prefix)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={"product_id": VALID_PRODUCT_ID},
            files=_make_csv_upload("garbage data"),
        )

        assert response.status_code == 400

    def test_non_admin_cannot_upsert(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Non-admin users should get 403."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        user_token = _create_regular_user(test_client, api_v1_prefix, admin_token)

        response = test_client.post(
            f"{api_v1_prefix}/admin/local_fints_configuration",
            headers={"Authorization": f"Bearer {user_token}"},
            data={"product_id": VALID_PRODUCT_ID},
            files=_make_csv_upload(),
        )

        assert response.status_code == 403


# =============================================================================
# Cross-endpoint workflows
# =============================================================================


class TestFinTSConfigWorkflow:
    """End-to-end workflow tests combining multiple endpoints."""

    def test_full_configuration_workflow(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Test the complete workflow: status → initial setup → verify → update."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}
        base = f"{api_v1_prefix}/admin/local_fints_configuration"

        # Step 1: Check status — not configured
        status_resp = test_client.get(f"{base}/status", headers=headers)
        assert status_resp.json()["is_configured"] is False

        # Step 2: Save initial configuration (Product ID + CSV)
        initial_resp = test_client.post(
            base,
            headers=headers,
            data={"product_id": VALID_PRODUCT_ID},
            files=_make_csv_upload(),
        )
        assert initial_resp.status_code == 200
        assert initial_resp.json()["institute_count"] == 2

        # Step 3: Check status — now configured
        status_resp = test_client.get(f"{base}/status", headers=headers)
        assert status_resp.json()["is_configured"] is True

        # Step 4: Get full configuration
        config_resp = test_client.get(base, headers=headers)
        assert config_resp.status_code == 200
        config = config_resp.json()
        assert config["csv_institute_count"] == 2
        assert len(config["product_id_masked"]) > 0

    def test_update_product_id_after_initial_setup(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Admin can update Product ID after initial configuration."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}
        base = f"{api_v1_prefix}/admin/local_fints_configuration"

        # Initial setup
        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        # Update Product ID only
        update_resp = test_client.post(
            base,
            headers=headers,
            data={"product_id": "NewProductID999"},
        )
        assert update_resp.status_code == 200

        # Verify the configuration details still show the product
        config_resp = test_client.get(base, headers=headers)
        assert config_resp.status_code == 200
        assert config_resp.json()["product_id_masked"] is not None

    def test_re_upload_csv_after_initial_setup(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Admin can re-upload CSV after initial configuration."""
        admin_token = _register_admin(test_client, api_v1_prefix)
        headers = {"Authorization": f"Bearer {admin_token}"}
        base = f"{api_v1_prefix}/admin/local_fints_configuration"

        # Initial setup with 2 institutes
        _setup_initial_config(test_client, api_v1_prefix, admin_token)

        # Re-upload with same CSV (CSV only)
        csv_resp = test_client.post(
            base,
            headers=headers,
            files=_make_csv_upload(),
        )
        assert csv_resp.status_code == 200
        assert csv_resp.json()["institute_count"] == 2
