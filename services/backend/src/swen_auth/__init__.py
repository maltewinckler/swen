"""SWEN Auth - Generic authentication infrastructure.

This package provides authentication infrastructure that is independent
of any specific application domain. It handles:
- Password hashing (bcrypt)
- JWT token creation and verification
- User credential storage (with pluggable persistence)

Architecture:
    swen_auth/
    ├── services/           # Pure logic (password hashing, JWT)
    ├── repositories/       # Abstract interfaces
    ├── persistence/        # Implementations by technology
    │   └── sqlalchemy/     # SQLAlchemy implementation
    ├── schemas.py          # Data classes
    └── exceptions.py       # Auth exceptions

Usage:
    # Import core services and interfaces
    from swen_auth import PasswordHashingService, JWTService

    # Import SQLAlchemy implementation
    from swen_auth.persistence.sqlalchemy import (
        UserCredentialRepositorySQLAlchemy,
        UserCredentialModel,
        AuthBase,
    )
"""

from swen_auth.exceptions import (
    AccountLockedError,
    AuthError,
    InvalidCredentialsError,
    InvalidTokenError,
    WeakPasswordError,
)
from swen_auth.repositories import UserCredentialRepository
from swen_auth.schemas import TokenPayload
from swen_auth.services import JWTService, PasswordHashingService

__all__ = [
    # Services
    "PasswordHashingService",
    "JWTService",
    # Repositories (interfaces)
    "UserCredentialRepository",
    # Schemas
    "TokenPayload",
    # Exceptions
    "AuthError",
    "InvalidTokenError",
    "WeakPasswordError",
    "InvalidCredentialsError",
    "AccountLockedError",
]

