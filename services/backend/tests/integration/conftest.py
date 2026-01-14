"""Integration test configuration and fixtures.

This conftest provides common fixtures for integration tests, including
the CurrentUser required by user-scoped repositories.
"""

from uuid import UUID

import pytest

from swen.application.ports.identity import CurrentUser

# Common test user IDs
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

ALICE_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ALICE_USER_EMAIL = "alice@example.com"

BOB_USER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
BOB_USER_EMAIL = "bob@example.com"


@pytest.fixture
def current_user() -> CurrentUser:
    """Provide a CurrentUser for the default test user."""
    return CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


@pytest.fixture
def alice_current_user() -> CurrentUser:
    """Provide a CurrentUser for Alice (multi-user testing)."""
    return CurrentUser(user_id=ALICE_USER_ID, email=ALICE_USER_EMAIL)


@pytest.fixture
def bob_current_user() -> CurrentUser:
    """Provide a CurrentUser for Bob (multi-user testing)."""
    return CurrentUser(user_id=BOB_USER_ID, email=BOB_USER_EMAIL)
