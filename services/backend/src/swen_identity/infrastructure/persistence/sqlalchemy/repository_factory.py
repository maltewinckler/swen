"""SQLAlchemy implementation of swen_identity's RepositoryFactory Protocol."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from swen_identity.application.factories.repository_factory import RepositoryFactory
from swen_identity.infrastructure.persistence.sqlalchemy.repositories import (
    PasswordResetTokenRepositorySQLAlchemy,
    UserCredentialRepositorySQLAlchemy,
    UserRepositorySQLAlchemy,
)
from swen_identity.infrastructure.persistence.sqlalchemy.unit_of_work import (
    UnitOfWorkSQLAlchemy,
)


class RepositoryFactorySQLAlchemy(RepositoryFactory):
    """SQLAlchemy implementation of swen_identity RepositoryFactory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def unit_of_work(self) -> UnitOfWorkSQLAlchemy:
        return UnitOfWorkSQLAlchemy(self._session)

    def user_repository(self) -> UserRepositorySQLAlchemy:
        return UserRepositorySQLAlchemy(self._session)

    def user_credential_repository(self) -> UserCredentialRepositorySQLAlchemy:
        return UserCredentialRepositorySQLAlchemy(self._session)

    def password_reset_token_repository(self) -> PasswordResetTokenRepositorySQLAlchemy:
        return PasswordResetTokenRepositorySQLAlchemy(self._session)
