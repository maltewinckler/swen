"""Integration test configuration and fixtures.

This conftest provides common fixtures for integration tests, including
the UserContext required by user-scoped repositories.
"""

from uuid import UUID

import pytest

from swen.application.context import UserContext


# Common test user IDs
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

ALICE_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ALICE_USER_EMAIL = "alice@example.com"

BOB_USER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
BOB_USER_EMAIL = "bob@example.com"


@pytest.fixture
def user_context() -> UserContext:
    """Provide a UserContext for the default test user."""
    return UserContext(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


@pytest.fixture
def alice_user_context() -> UserContext:
    """Provide a UserContext for Alice (multi-user testing)."""
    return UserContext(user_id=ALICE_USER_ID, email=ALICE_USER_EMAIL)


@pytest.fixture
def bob_user_context() -> UserContext:
    """Provide a UserContext for Bob (multi-user testing)."""
    return UserContext(user_id=BOB_USER_ID, email=BOB_USER_EMAIL)

