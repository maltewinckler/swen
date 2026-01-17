"""
Pytest configuration for swen_identity domain tests.

This conftest provides fixtures specific to the swen_identity domain
(users, authentication, authorization).
"""

import pytest

from swen_identity.domain.user import User, UserRole


@pytest.fixture
def test_user() -> User:
    """Create a standard test user."""
    return User.create("test@example.com")


@pytest.fixture
def admin_user() -> User:
    """Create an admin test user."""
    user = User.create("admin@example.com")
    user.promote_to_admin()
    return user


@pytest.fixture
def user_role() -> UserRole:
    """Standard user role."""
    return UserRole.USER


@pytest.fixture
def admin_role() -> UserRole:
    """Admin user role."""
    return UserRole.ADMIN
