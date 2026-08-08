"""Command to change a user's password."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen_identity.domain.services import AuthenticationService

if TYPE_CHECKING:
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory
    from swen_identity.application.ports.unit_of_work import UnitOfWork


class ChangePasswordCommand:
    """Change the current user's password after verifying the old one."""

    def __init__(self, auth_service: AuthenticationService, uow: UnitOfWork):
        self._auth_service = auth_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
    ) -> ChangePasswordCommand:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_hashing_port=adapter_factory.password_hashing_port(),
                token_handling_port=adapter_factory.token_handling_port(),
            ),
            uow=factory.unit_of_work(),
        )

    async def execute(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        async with self._uow:
            await self._auth_service.change_password(
                user_id=user_id,
                current_password=current_password,
                new_password=new_password,
            )
