"""
Pytest configuration for swen domain tests.

This conftest provides fixtures specific to the swen domain
(banking, accounting, integration contexts).
"""

from unittest.mock import AsyncMock

import pytest

from swen.domain.shared.current_user import CurrentUser
from tests.shared.fixtures.factories import TestUserFactory


@pytest.fixture
def current_user() -> CurrentUser:
    """Provide a CurrentUser for the default test user."""
    return TestUserFactory.default_current_user()


@pytest.fixture
def mock_uow() -> AsyncMock:
    """No-op UnitOfWork for unit tests that mock out the session entirely."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def alice_current_user() -> CurrentUser:
    """Provide a CurrentUser for Alice (multi-user testing)."""
    return TestUserFactory.alice_current_user()


@pytest.fixture
def bob_current_user() -> CurrentUser:
    """Provide a CurrentUser for Bob (multi-user testing)."""
    return TestUserFactory.bob_current_user()
