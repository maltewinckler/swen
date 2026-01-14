"""SQLAlchemy implementation for swen_identity persistence.

Provides:
- IdentityBase: Declarative base for identity models
- UserModel: SQLAlchemy model for users
- UserCredentialModel: SQLAlchemy model for credentials
- PasswordResetTokenModel: SQLAlchemy model for password reset tokens
- UserRepositorySQLAlchemy: Repository implementation for users
- UserCredentialRepositorySQLAlchemy: Repository implementation for credentials
- PasswordResetTokenRepositorySQLAlchemy: Repository implementation for tokens
"""

from swen_identity.infrastructure.persistence.sqlalchemy.base import IdentityBase
from swen_identity.infrastructure.persistence.sqlalchemy.models import (
    PasswordResetTokenModel,
    UserCredentialModel,
    UserModel,
)
from swen_identity.infrastructure.persistence.sqlalchemy.repositories import (
    PasswordResetTokenRepositorySQLAlchemy,
    UserCredentialRepositorySQLAlchemy,
    UserRepositorySQLAlchemy,
)

__all__ = [
    "IdentityBase",
    "PasswordResetTokenModel",
    "PasswordResetTokenRepositorySQLAlchemy",
    "UserCredentialModel",
    "UserCredentialRepositorySQLAlchemy",
    "UserModel",
    "UserRepositorySQLAlchemy",
]
