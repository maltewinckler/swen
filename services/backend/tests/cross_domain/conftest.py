"""
Pytest configuration for cross-domain tests.

These tests span multiple bounded contexts (swen + swen_identity)
and test their interactions.
"""

# Re-export shared database fixtures for integration tests
from tests.shared.fixtures.database import (
    async_engine,
    db_session,
    postgres_container,
)
from tests.shared.fixtures.factories import TestUserFactory

__all__ = [
    "async_engine",
    "db_session",
    "postgres_container",
    "TestUserFactory",
]
