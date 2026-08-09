"""Query to resolve the authenticated user from an access token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.context import UserContext
from swen_identity.domain.services import AuthenticationService

if TYPE_CHECKING:
    from swen_identity.application.factories import AdapterFactory, RepositoryFactory


class GetCurrentUserQuery:
    """Resolve the currently authenticated user's public representation."""

    def __init__(self, auth_service: AuthenticationService):
        self._auth_service = auth_service

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        adapter_factory: AdapterFactory,
    ) -> GetCurrentUserQuery:
        return cls(
            auth_service=AuthenticationService(
                user_repository=factory.user_repository(),
                credential_repository=factory.user_credential_repository(),
                password_hashing_port=adapter_factory.password_hashing_port(),
                token_handling_port=adapter_factory.token_handling_port(),
            ),
        )

    async def execute(self, access_token: str) -> UserContext:
        user = await self._auth_service.get_authenticated_user(access_token)
        return UserContext.create(user)
