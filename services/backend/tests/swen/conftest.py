"""
Pytest configuration for swen domain tests.

This conftest provides fixtures specific to the swen domain
(banking, accounting, integration contexts).
"""

import pytest

from swen.application.ports.identity import CurrentUser
from tests.shared.fixtures.factories import TestUserFactory


@pytest.fixture
def current_user() -> CurrentUser:
    """Provide a CurrentUser for the default test user."""
    return TestUserFactory.default_current_user()


@pytest.fixture
def alice_current_user() -> CurrentUser:
    """Provide a CurrentUser for Alice (multi-user testing)."""
    return TestUserFactory.alice_current_user()


@pytest.fixture
def bob_current_user() -> CurrentUser:
    """Provide a CurrentUser for Bob (multi-user testing)."""
    return TestUserFactory.bob_current_user()
