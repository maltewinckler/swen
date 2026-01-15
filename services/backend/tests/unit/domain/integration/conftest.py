"""Common fixtures for integration domain tests."""

from uuid import UUID

import pytest


@pytest.fixture
def test_user_id() -> UUID:
    """Provide a consistent test user ID for all integration domain tests."""
    return UUID("12345678-1234-5678-1234-567812345678")
