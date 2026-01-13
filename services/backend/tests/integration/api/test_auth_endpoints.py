"""Integration tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, test_client: TestClient, api_v1_prefix: str):
        """Successfully register a new user."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert "id" in data["user"]
        assert "created_at" in data["user"]
        assert "role" in data["user"]  # Role should be present

        assert "access_token" in data
        # refresh_token is now sent via HttpOnly cookie, not in body
        assert data["refresh_token"] is None
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

        # Verify refresh token cookie is set
        assert "swen_refresh_token" in response.cookies

    def test_register_duplicate_email(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Cannot create user with duplicate email via admin endpoint."""
        # First registration (becomes admin)
        response1 = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        assert response1.status_code == 201
        admin_token = response1.json()["access_token"]

        # Try to create another user with same email via admin endpoint
        response2 = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": registered_user_data["email"],
                "password": "AnotherPassword123!",
            },
        )
        assert response2.status_code == 409
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_weak_password(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot register with a weak password."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "short",  # Too short (< 8 chars triggers Pydantic validation)
            },
        )

        # Pydantic validation returns 422 for min_length violation
        assert response.status_code == 422

    def test_register_invalid_email(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot register with an invalid email format."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Successfully log in with valid credentials."""
        # Register first
        test_client.post(f"{api_v1_prefix}/auth/register", json=registered_user_data)

        # Login
        response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={
                "email": registered_user_data["email"],
                "password": registered_user_data["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert data["user"]["email"] == registered_user_data["email"]
        assert "access_token" in data
        # refresh_token is now sent via HttpOnly cookie, not in body
        assert data["refresh_token"] is None

        # Verify refresh token cookie is set
        assert "swen_refresh_token" in response.cookies

    def test_login_wrong_password(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Cannot log in with wrong password."""
        # Register first
        test_client.post(f"{api_v1_prefix}/auth/register", json=registered_user_data)

        # Login with wrong password
        response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={
                "email": registered_user_data["email"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_unknown_email(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot log in with non-existent email."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={
                "email": "unknown@example.com",
                "password": "AnyPassword123!",
            },
        )

        assert response.status_code == 401
        # Should not reveal whether email exists
        assert "invalid" in response.json()["detail"].lower()


class TestAuthRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    def test_refresh_success_via_cookie(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Successfully refresh tokens using HttpOnly cookie."""
        # Register - this sets the refresh token cookie
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        assert "swen_refresh_token" in register_response.cookies

        # Refresh - the cookie is automatically sent
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={},  # Empty body - token is in cookie
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        # refresh_token is now sent via HttpOnly cookie, not in body
        assert data["refresh_token"] is None
        assert data["token_type"] == "bearer"

        # Verify new refresh token cookie is set (rotation)
        assert "swen_refresh_token" in response.cookies

    def test_refresh_success_via_body(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Successfully refresh tokens using body (backward compatibility)."""
        # Register and get refresh token from cookie
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        refresh_token = register_response.cookies.get("swen_refresh_token")

        # Clear cookies on the test client to simulate body-only refresh
        test_client.cookies.clear()

        # Refresh using body (no cookie)
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_invalid_token(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot refresh with invalid token."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    def test_refresh_no_token(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot refresh without any token."""
        # Clear any existing cookies by using fresh client
        from fastapi.testclient import TestClient as TC
        from swen.presentation.api.app import create_app

        fresh_client = TC(create_app())

        response = fresh_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={},
        )

        assert response.status_code == 401
        assert "no refresh token" in response.json()["detail"].lower()

    def test_refresh_with_access_token(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Cannot use access token as refresh token."""
        # Register and get access token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        access_token = register_response.json()["access_token"]

        # Try to refresh with access token in body
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestAuthMe:
    """Tests for GET /api/v1/auth/me."""

    def test_get_me_success(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Get current user info with valid token."""
        # Register and get token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        token = register_response.json()["access_token"]

        # Get me
        response = test_client.get(
            f"{api_v1_prefix}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == registered_user_data["email"]
        assert "id" in data
        assert "created_at" in data
        assert "role" in data  # Role should be present

    def test_get_me_no_token(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot get user info without token."""
        response = test_client.get(f"{api_v1_prefix}/auth/me")

        assert response.status_code == 401

    def test_get_me_invalid_token(self, test_client: TestClient, api_v1_prefix: str):
        """Cannot get user info with invalid token."""
        response = test_client.get(
            f"{api_v1_prefix}/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestAuthChangePassword:
    """Tests for POST /api/v1/auth/change-password."""

    def test_change_password_success(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Successfully change password."""
        # Register and get token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        token = register_response.json()["access_token"]

        # Change password
        response = test_client.post(
            f"{api_v1_prefix}/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": registered_user_data["password"],
                "new_password": "NewSecurePassword456!",
            },
        )

        assert response.status_code == 204

        # Verify can login with new password
        login_response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={
                "email": registered_user_data["email"],
                "password": "NewSecurePassword456!",
            },
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Cannot change password with wrong current password."""
        # Register and get token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        token = register_response.json()["access_token"]

        # Try to change with wrong current password
        response = test_client.post(
            f"{api_v1_prefix}/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePassword456!",
            },
        )

        assert response.status_code == 401

    def test_change_password_weak_new(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Cannot change to a weak password."""
        # Register and get token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        token = register_response.json()["access_token"]

        # Try to change to weak password
        response = test_client.post(
            f"{api_v1_prefix}/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": registered_user_data["password"],
                "new_password": "weak",  # < 8 chars triggers Pydantic validation
            },
        )

        # Pydantic validation returns 422 for min_length violation
        assert response.status_code == 422


class TestTokenTypeSecurity:
    """Tests for token type enforcement (security).

    Ensures refresh tokens cannot be used as access tokens and vice versa.
    This prevents attackers from using long-lived refresh tokens to access
    protected endpoints.
    """

    def test_refresh_token_rejected_for_protected_endpoints(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Refresh tokens cannot be used to access protected endpoints."""
        # Register and get refresh token from cookie
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        refresh_token = register_response.cookies.get("swen_refresh_token")

        # Try to use refresh token as access token on /auth/me
        response = test_client.get(
            f"{api_v1_prefix}/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 401
        assert "invalid token type" in response.json()["detail"].lower()

    def test_refresh_token_rejected_for_accounts_endpoint(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Refresh tokens cannot be used to access /accounts endpoint."""
        # Register and get refresh token from cookie
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        refresh_token = register_response.cookies.get("swen_refresh_token")

        # Try to use refresh token on a different protected endpoint
        response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 401
        assert "invalid token type" in response.json()["detail"].lower()

    def test_access_token_works_for_protected_endpoints(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Access tokens work correctly for protected endpoints."""
        # Register and get access token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        access_token = register_response.json()["access_token"]

        # Use access token on /auth/me - should work
        response = test_client.get(
            f"{api_v1_prefix}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["email"] == registered_user_data["email"]

    def test_access_token_rejected_for_refresh(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Access tokens cannot be used to refresh."""
        # Register and get access token
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )
        access_token = register_response.json()["access_token"]

        # Try to use access token for refresh
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401

    def test_refresh_token_works_for_refresh_endpoint(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Refresh tokens work correctly for the refresh endpoint (via cookie)."""
        # Register - this sets the refresh token cookie
        test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )

        # Use refresh token via cookie for refresh - should work
        response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()


class TestHttpOnlyCookieSecurity:
    """Tests for HttpOnly cookie security features.

    Verifies that refresh tokens are properly secured via HttpOnly cookies
    and that logout properly clears cookies.
    """

    def test_login_sets_httponly_cookie(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Login sets refresh token as HttpOnly cookie."""
        # Register first
        test_client.post(f"{api_v1_prefix}/auth/register", json=registered_user_data)

        # Login
        response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={
                "email": registered_user_data["email"],
                "password": registered_user_data["password"],
            },
        )

        assert response.status_code == 200
        assert "swen_refresh_token" in response.cookies

        # Cookie should have proper path restriction
        cookie = response.cookies.get("swen_refresh_token")
        assert cookie is not None

    def test_register_sets_httponly_cookie(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Register sets refresh token as HttpOnly cookie."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": "cookietest@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 201
        assert "swen_refresh_token" in response.cookies

    def test_refresh_sets_new_cookie(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Refresh endpoint sets a new refresh token cookie."""
        # Register
        test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )

        # Refresh
        refresh_response = test_client.post(
            f"{api_v1_prefix}/auth/refresh",
            json={},
        )

        assert refresh_response.status_code == 200

        # New cookie should be set
        new_cookie = refresh_response.cookies.get("swen_refresh_token")
        assert new_cookie is not None
        assert len(new_cookie) > 0

    def test_logout_clears_cookie(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Logout clears the refresh token cookie."""
        # Register
        test_client.post(f"{api_v1_prefix}/auth/register", json=registered_user_data)

        # Logout
        response = test_client.post(f"{api_v1_prefix}/auth/logout")

        assert response.status_code == 204

    def test_logout_works_without_auth(
        self, test_client: TestClient, api_v1_prefix: str
    ):
        """Logout works without authentication (clears cookie regardless)."""
        # Just call logout without being logged in
        response = test_client.post(f"{api_v1_prefix}/auth/logout")

        assert response.status_code == 204

    def test_refresh_token_not_in_response_body(
        self, test_client: TestClient, registered_user_data: dict, api_v1_prefix: str
    ):
        """Refresh token is not exposed in response body (only in cookie)."""
        # Register
        response = test_client.post(
            f"{api_v1_prefix}/auth/register", json=registered_user_data
        )

        data = response.json()

        # refresh_token should be None in body (sent via cookie)
        assert data.get("refresh_token") is None

        # But cookie should be set
        assert "swen_refresh_token" in response.cookies


class TestHealthEndpoint:
    """Tests for GET /health (unversioned)."""

    def test_health_check(self, test_client: TestClient):
        """Health check returns ok."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "api_versions" in data
        assert "v1" in data["api_versions"]


class TestRootEndpoint:
    """Tests for GET / (API info)."""

    def test_root_info(self, test_client: TestClient, api_v1_prefix: str):
        """Root endpoint returns API info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert data["api_base"] == api_v1_prefix
        assert "endpoints" in data
