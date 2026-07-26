"""SQLAlchemy implementation of swen_identity's RepositoryFactory Protocol."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from swen_identity.infrastructure.persistence.sqlalchemy.repositories import (
    UserCredentialRepositorySQLAlchemy,
    UserRepositorySQLAlchemy,
)
from swen_identity.infrastructure.persistence.sqlalchemy.unit_of_work import (
    UnitOfWorkSQLAlchemy,
)


class RepositoryFactorySQLAlchemy:
    """SQLAlchemy implementation of swen_identity's RepositoryFactory Protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

        # Cached instances (created on demand)
        self._user_repo: UserRepositorySQLAlchemy | None = None
        self._credential_repo: UserCredentialRepositorySQLAlchemy | None = None

    def unit_of_work(self) -> UnitOfWorkSQLAlchemy:
        return UnitOfWorkSQLAlchemy(self._session)

    def user_repository(self) -> UserRepositorySQLAlchemy:
        if self._user_repo is None:
            self._user_repo = UserRepositorySQLAlchemy(self._session)
        return self._user_repo

    def user_credential_repository(self) -> UserCredentialRepositorySQLAlchemy:
        if self._credential_repo is None:
            self._credential_repo = UserCredentialRepositorySQLAlchemy(self._session)
        return self._credential_repo
