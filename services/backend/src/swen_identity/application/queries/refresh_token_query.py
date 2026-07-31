"""Query to refresh an access/refresh token pair from a valid refresh token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.services import AuthenticationService
from swen_identity.services import JWTService, PasswordHashingService

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class RefreshTokenQuery:
    """Issue a new access/refresh token pair from a valid refresh token.

    Read-only: verifies the token and looks up the user, no repository
    writes — so unlike the auth Commands, this needs no UnitOfWork.
    """

    def __init__(self, auth_service: AuthenticationService):
        self._auth_service = auth_service

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        jwt_service: JWTService,
        password_service: PasswordHashingService,
    ) -> RefreshTokenQuery:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_service=password_service,
                jwt_service=jwt_service,
            ),
        )

    async def execute(self, refresh_token: str) -> tuple[str, str]:
        return await self._auth_service.refresh_token(refresh_token=refresh_token)
