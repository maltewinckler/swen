"""Command to register a new user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.application.services import AuthenticationService
from swen_identity.domain import User
from swen_identity.services import JWTService, PasswordHashingService

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class RegisterCommand:
    """Register a new user and issue an initial access/refresh token pair."""

    def __init__(self, auth_service: AuthenticationService, uow: UnitOfWork):
        self._auth_service = auth_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        jwt_service: JWTService,
        password_service: PasswordHashingService,
    ) -> RegisterCommand:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_service=password_service,
                jwt_service=jwt_service,
            ),
            uow=factory.unit_of_work(),
        )

    async def execute(self, email: str, password: str) -> tuple[User, str, str]:
        async with self._uow:
            return await self._auth_service.register(email=email, password=password)
