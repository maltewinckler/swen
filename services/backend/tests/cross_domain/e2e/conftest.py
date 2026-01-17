"""
E2E test fixtures for critical user journeys.

These tests simulate complete user flows through the API, testing
the integration of multiple endpoints in realistic scenarios.
"""

import pytest

# Import fixtures from integration conftest (sibling directory).
# Pytest doesn't auto-discover fixtures from sibling directories,
# so we need to explicitly import and re-export them.
# These imports are used by pytest's fixture discovery, not directly in code.
from tests.cross_domain.integration.conftest import (
    api_settings,  # noqa: F401
    api_v1_prefix,  # noqa: F401
    async_engine,  # noqa: F401
    auth_headers,  # noqa: F401
    db_session,  # noqa: F401
    mock_encryption_key,  # noqa: F401
    postgres_container,  # noqa: F401
    registered_user_data,  # noqa: F401
    test_client,  # noqa: F401
)


@pytest.fixture
def new_user_email():
    """Generate a unique email for E2E tests to avoid conflicts."""
    import uuid

    return f"e2e-user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def e2e_user_data(new_user_email):
    """E2E test user registration data."""
    return {
        "email": new_user_email,
        "password": "E2ETestPassword123!",
    }


@pytest.fixture
def authenticated_user(test_client, e2e_user_data, api_v1_prefix):  # noqa: F811
    """Register a user and return their auth context.

    Returns a dict with:
    - headers: Authorization headers for API calls
    - user_id: The registered user's UUID
    - email: The user's email
    - access_token: The JWT access token
    """
    response = test_client.post(
        f"{api_v1_prefix}/auth/register",
        json=e2e_user_data,
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"

    data = response.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user_id": data["user"]["id"],
        "email": data["user"]["email"],
        "access_token": data["access_token"],
    }


@pytest.fixture
def user_with_chart(test_client, authenticated_user, api_v1_prefix):  # noqa: F811
    """A user with initialized chart of accounts.

    Returns the authenticated_user dict with an additional 'chart' key
    containing the chart initialization response.
    """
    response = test_client.post(
        f"{api_v1_prefix}/accounts/init-chart",
        headers=authenticated_user["headers"],
        json={"template": "minimal"},
    )
    assert response.status_code == 201, f"Chart init failed: {response.text}"

    return {
        **authenticated_user,
        "chart": response.json(),
    }
