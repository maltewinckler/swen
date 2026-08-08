"""Command to request a password reset email."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.services import PasswordResetService
from swen_identity.infrastructure.email import EmailService

if TYPE_CHECKING:
    from swen_config.settings import Settings
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory
    from swen_identity.application.ports.unit_of_work import UnitOfWork


class ForgotPasswordCommand:
    """Request a password reset email (silently no-ops for an unknown email)."""

    def __init__(self, reset_service: PasswordResetService, uow: UnitOfWork):
        self._reset_service = reset_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
        settings: Settings,
    ) -> ForgotPasswordCommand:
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

    async def execute(self, email: str) -> None:
        async with self._uow:
            await self._reset_service.request_reset(email)
