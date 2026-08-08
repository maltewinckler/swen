from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.domain import (
    EmailAlreadyExistsError,
    User,
    UserCredentialRepository,
    UserRepository,
    UserRole,
)
from swen_identity.domain.ports import PasswordHashingPort

if TYPE_CHECKING:
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory
    from swen_identity.application.ports.unit_of_work import UnitOfWork


class CreateUserCommand:
    """Command to create a new user."""

    def __init__(
        self,
        user_repository: UserRepository,
        credential_repository: UserCredentialRepository,
        password_hashing_port: PasswordHashingPort,
        uow: UnitOfWork,
    ):
        self._user_repo = user_repository
        self._credential_repo = credential_repository
        self._password_hashing_port = password_hashing_port
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
    ) -> CreateUserCommand:
        return cls(
            user_repository=factory.user_repository(),
            credential_repository=factory.user_credential_repository(),
            password_hashing_port=adapter_factory.password_hashing_port(),
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
            password_hash = self._password_hashing_port.hash(password)

            await self._user_repo.save(user)
            await self._credential_repo.save(
                user_id=user.id,
                password_hash=password_hash,
            )

            return user
