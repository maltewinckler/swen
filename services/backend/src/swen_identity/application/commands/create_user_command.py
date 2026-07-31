from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.domain.user import (
    EmailAlreadyExistsError,
    User,
    UserRepository,
    UserRole,
)
from swen_identity.repositories import UserCredentialRepository
from swen_identity.services import PasswordHashingService

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class CreateUserCommand:
    """Command to create a new user."""

    def __init__(
        self,
        user_repository: UserRepository,
        credential_repository: UserCredentialRepository,
        password_service: PasswordHashingService,
        uow: UnitOfWork,
    ):
        self._user_repo = user_repository
        self._credential_repo = credential_repository
        self._password_service = password_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        password_service: PasswordHashingService,
    ) -> CreateUserCommand:
        return cls(
            user_repository=factory.user_repository(),
            credential_repository=factory.user_credential_repository(),
            password_service=password_service,
            uow=factory.unit_of_work(),
        )

    async def execute(
        self,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        async with self._uow:
            existing = await self._user_repo.find_by_email(email)
            if existing:
                raise EmailAlreadyExistsError(email)

            user = User.create(email, role=role)
            password_hash = self._password_service.hash(password)

            await self._user_repo.save(user)
            await self._credential_repo.save(
                user_id=user.id, password_hash=password_hash
            )

            return user
