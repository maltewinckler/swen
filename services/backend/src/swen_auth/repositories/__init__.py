"""Repository interfaces for swen_auth.

This package defines abstract repository interfaces that can be implemented
by different persistence technologies (SQLAlchemy, MongoDB, etc.).

The actual implementations live in the consuming application's infrastructure
layer (e.g., swen/infrastructure/persistence/sqlalchemy/repositories/auth/).
"""

from swen_auth.repositories.user_credential_repository import (
    UserCredentialData,
    UserCredentialRepository,
)

__all__ = ["UserCredentialData", "UserCredentialRepository"]
