"""Command to register a new user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.domain import User
from swen_identity.domain.services import AuthenticationService

if TYPE_CHECKING:
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory
    from swen_identity.application.ports.unit_of_work import UnitOfWork


class RegisterCommand:
    """Register a new user and issue an initial access/refresh token pair."""

    def __init__(self, auth_service: AuthenticationService, uow: UnitOfWork):
        self._auth_service = auth_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
    ) -> RegisterCommand:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_hashing_port=adapter_factory.password_hashing_port(),
                token_handling_port=adapter_factory.token_handling_port(),
            ),
            uow=factory.unit_of_work(),
        )

    async def execute(self, email: str, password: str) -> tuple[User, str, str]:
        async with self._uow:
            return await self._auth_service.register(email=email, password=password)
