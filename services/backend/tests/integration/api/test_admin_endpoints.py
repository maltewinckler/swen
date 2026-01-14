"""Integration tests for admin endpoints."""

from fastapi.testclient import TestClient


class TestAdminListUsers:
    """Tests for GET /api/v1/admin/users."""

    def test_list_users_as_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can list all users."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        assert register_response.status_code == 201
        admin_token = register_response.json()["access_token"]

        # List users
        response = test_client.get(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        users = response.json()
        assert len(users) == 1
        assert users[0]["email"] == "admin@example.com"
        assert users[0]["role"] == "admin"
        assert "id" in users[0]
        assert "created_at" in users[0]

    def test_list_users_as_non_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Non-admin cannot list users."""
        # Register first user (becomes admin)
        admin_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = admin_response.json()["access_token"]

        # Create a non-admin user via admin endpoint
        test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "user@example.com", "password": "SecurePassword123!"},
        )

        # Login as the non-admin user
        login_response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={"email": "user@example.com", "password": "SecurePassword123!"},
        )
        user_token = login_response.json()["access_token"]

        # Try to list users
        response = test_client.get(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_list_users_without_auth(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Unauthenticated request cannot list users."""
        response = test_client.get(f"{api_v1_prefix}/admin/users")
        assert response.status_code == 401


class TestAdminCreateUser:
    """Tests for POST /api/v1/admin/users."""

    def test_create_user_as_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can create a new user."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create new user
        response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newuser@example.com",
                "password": "NewUserPassword123!",
                "role": "user",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data

    def test_create_admin_user(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can create another admin."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create new admin
        response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newadmin@example.com",
                "password": "NewAdminPassword123!",
                "role": "admin",
            },
        )

        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    def test_create_user_duplicate_email(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Cannot create user with duplicate email."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Try to create user with same email
        response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "admin@example.com",
                "password": "AnotherPassword123!",
            },
        )

        assert response.status_code == 409

    def test_create_user_invalid_role(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Invalid role returns 400."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newuser@example.com",
                "password": "Password123!",
                "role": "superadmin",  # Invalid role
            },
        )

        assert response.status_code == 400

    def test_create_user_as_non_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Non-admin cannot create users."""
        # Register first user (becomes admin)
        admin_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = admin_response.json()["access_token"]

        # Create a non-admin user via admin endpoint
        test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "user@example.com", "password": "SecurePassword123!"},
        )

        # Login as the non-admin user
        login_response = test_client.post(
            f"{api_v1_prefix}/auth/login",
            json={"email": "user@example.com", "password": "SecurePassword123!"},
        )
        user_token = login_response.json()["access_token"]

        # Try to create user
        response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "email": "newuser@example.com",
                "password": "Password123!",
            },
        )

        assert response.status_code == 403


class TestAdminDeleteUser:
    """Tests for DELETE /api/v1/admin/users/{user_id}."""

    def test_delete_user_as_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can delete a user."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create a user to delete
        create_response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "todelete@example.com", "password": "Password123!"},
        )
        user_id = create_response.json()["id"]

        # Delete the user
        response = test_client.delete(
            f"{api_v1_prefix}/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 204

        # Verify user is deleted
        list_response = test_client.get(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        emails = [u["email"] for u in list_response.json()]
        assert "todelete@example.com" not in emails

    def test_delete_self_fails(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin cannot delete themselves."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]
        admin_id = register_response.json()["user"]["id"]

        # Try to delete self
        response = test_client.delete(
            f"{api_v1_prefix}/admin/users/{admin_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "delete" in response.json()["detail"].lower()

    def test_delete_nonexistent_user(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Deleting non-existent user returns 404."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Try to delete non-existent user
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.delete(
            f"{api_v1_prefix}/admin/users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404


class TestAdminUpdateUserRole:
    """Tests for PATCH /api/v1/admin/users/{user_id}/role."""

    def test_promote_user_to_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can promote a user to admin."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create a regular user
        create_response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "user@example.com", "password": "Password123!"},
        )
        user_id = create_response.json()["id"]

        # Promote to admin
        response = test_client.patch(
            f"{api_v1_prefix}/admin/users/{user_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "admin"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_demote_admin_to_user(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin can demote another admin to user."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create another admin
        create_response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "admin2@example.com", "password": "Password123!", "role": "admin"},
        )
        admin2_id = create_response.json()["id"]

        # Demote to user
        response = test_client.patch(
            f"{api_v1_prefix}/admin/users/{admin2_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "user"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "user"

    def test_demote_self_fails(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Admin cannot demote themselves."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]
        admin_id = register_response.json()["user"]["id"]

        # Try to demote self
        response = test_client.patch(
            f"{api_v1_prefix}/admin/users/{admin_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "user"},
        )

        assert response.status_code == 400
        assert "demote" in response.json()["detail"].lower()

    def test_update_nonexistent_user_role(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Updating non-existent user returns 404."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.patch(
            f"{api_v1_prefix}/admin/users/{fake_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "admin"},
        )

        assert response.status_code == 404

    def test_update_role_invalid_role(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Invalid role returns 400."""
        # Register first user (becomes admin)
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = register_response.json()["access_token"]

        # Create a user
        create_response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "user@example.com", "password": "Password123!"},
        )
        user_id = create_response.json()["id"]

        response = test_client.patch(
            f"{api_v1_prefix}/admin/users/{user_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "superadmin"},  # Invalid
        )

        assert response.status_code == 400


class TestFirstUserIsAdmin:
    """Tests for first-user-is-admin behavior."""

    def test_first_registered_user_is_admin(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """First registered user becomes admin."""
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "first@example.com", "password": "SecurePassword123!"},
        )

        assert response.status_code == 201
        assert response.json()["user"]["role"] == "admin"

    def test_admin_created_user_is_not_admin_by_default(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Users created by admin are regular users by default."""
        # First user (admin)
        admin_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "admin@example.com", "password": "SecurePassword123!"},
        )
        admin_token = admin_response.json()["access_token"]

        # Create second user via admin endpoint (default role)
        create_response = test_client.post(
            f"{api_v1_prefix}/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "second@example.com", "password": "SecurePassword123!"},
        )

        assert create_response.status_code == 201
        assert create_response.json()["role"] == "user"

    def test_public_registration_blocked_after_first_user(
        self, test_client: TestClient, api_v1_prefix: str,
    ):
        """Public registration is blocked after first user (admin_only mode)."""
        # First user (becomes admin)
        test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "first@example.com", "password": "SecurePassword123!"},
        )

        # Try to register second user publicly
        response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": "second@example.com", "password": "SecurePassword123!"},
        )

        # Should be forbidden in admin_only mode
        assert response.status_code == 403
        assert "registration" in response.json()["detail"].lower()
