"""System adapters - SQLAlchemy implementations of system ports."""

from swen.infrastructure.persistence.sqlalchemy.adapters.system.sqlalchemy_database_integrity_adapter import (  # NOQA: E501
    SqlAlchemyDatabaseIntegrityAdapter,
)

__all__ = ["SqlAlchemyDatabaseIntegrityAdapter"]
