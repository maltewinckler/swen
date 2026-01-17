"""
Pytest configuration for swen_identity integration tests.

Integration tests use Testcontainers for an ephemeral PostgreSQL instance.
Import the shared fixtures to make them available.
"""

# Re-export shared database fixtures
from tests.shared.fixtures.database import (
    async_engine,
    db_session,
    postgres_container,
)

__all__ = [
    "async_engine",
    "db_session",
    "postgres_container",
]
