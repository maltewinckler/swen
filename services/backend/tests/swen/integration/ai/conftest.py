"""Pytest fixtures for AI integration tests.

Re-exports fixtures from parent API conftest to make them available to AI tests.
"""

# Import and re-export fixtures from the parent API conftest
from tests.swen.integration.api.conftest import (
    api_settings,
    api_v1_prefix,
    auth_headers,
    authenticated_user,
    mock_encryption_key,
    registered_user_data,
    test_client,
)

__all__ = [
    "api_settings",
    "api_v1_prefix",
    "authenticated_user",
    "auth_headers",
    "mock_encryption_key",
    "registered_user_data",
    "test_client",
]
