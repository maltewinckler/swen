"""Command to reset a user's password using a reset token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.application.services import PasswordResetService
from swen_identity.infrastructure.email import EmailService

if TYPE_CHECKING:
    from swen_config.settings import Settings
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory


class ResetPasswordCommand:
    """Reset a user's password given a valid, unexpired reset token."""

    def __init__(self, reset_service: PasswordResetService, uow: UnitOfWork):
        self._reset_service = reset_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
        settings: Settings,
    ) -> ResetPasswordCommand:
        return cls(
            reset_service=PasswordResetService(
                user_repository=factory.user_repository(),
                token_repository=factory.password_reset_token_repository(),
                credential_repository=factory.user_credential_repository(),
                password_hashing_port=adapter_factory.password_hashing_port(),
                email_service=EmailService(settings),
                frontend_base_url=settings.frontend_base_url,
            ),
            uow=factory.unit_of_work(),
        )

    async def execute(self, token: str, new_password: str) -> None:
        async with self._uow:
            await self._reset_service.reset_password(
                token=token,
                new_password=new_password,
            )
