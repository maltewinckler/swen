"""SQLAlchemy implementation for swen_auth persistence.

Provides:
- AuthBase: Declarative base for auth models
- UserCredentialModel: SQLAlchemy model for credentials
- UserCredentialRepositorySQLAlchemy: Repository implementation

Note: The consuming application should include AuthBase.metadata
in its Alembic migrations to create the user_credentials table.

Examples
--------
# In your Alembic env.py or migration setup:
from swen_auth.persistence.sqlalchemy import AuthBase
target_metadata = [YourBase.metadata, AuthBase.metadata]
"""

from swen_auth.persistence.sqlalchemy.base import AuthBase
from swen_auth.persistence.sqlalchemy.models import (
    PasswordResetTokenModel,
    UserCredentialModel,
)
from swen_auth.persistence.sqlalchemy.repositories import (
    PasswordResetTokenRepositorySQLAlchemy,
    UserCredentialRepositorySQLAlchemy,
)

__all__ = [
    "AuthBase",
    "PasswordResetTokenModel",
    "PasswordResetTokenRepositorySQLAlchemy",
    "UserCredentialModel",
    "UserCredentialRepositorySQLAlchemy",
]
