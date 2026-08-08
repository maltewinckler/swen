"""Query to refresh an access/refresh token pair from a valid refresh token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.services import AuthenticationService

if TYPE_CHECKING:
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory


class RefreshTokenQuery:
    """Issue a new access/refresh token pair from a valid refresh token."""

    def __init__(self, auth_service: AuthenticationService):
        self._auth_service = auth_service

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
    ) -> RefreshTokenQuery:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_hashing_port=adapter_factory.password_hashing_port(),
                token_handling_port=adapter_factory.token_handling_port(),
            ),
        )

    async def execute(self, refresh_token: str) -> tuple[str, str]:
        return await self._auth_service.refresh_token(refresh_token=refresh_token)
