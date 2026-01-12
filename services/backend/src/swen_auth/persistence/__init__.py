"""Persistence implementations for swen_auth.

This package contains database-specific implementations of the
repository interfaces defined in swen_auth.repositories.

Structure:
    persistence/
    ├── sqlalchemy/     # SQLAlchemy/SQL database implementation
    └── (future)        # mongodb/, dynamodb/, etc.

Usage:
    from swen_auth.persistence.sqlalchemy import (
        UserCredentialRepositorySQLAlchemy,
        UserCredentialModel,
        AuthBase,
    )
"""

