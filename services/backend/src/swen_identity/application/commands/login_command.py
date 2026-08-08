"""Command to authenticate a user with email and password."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.application.services import AuthenticationService
from swen_identity.domain import User
from swen_identity.exceptions import AccountLockedError, InvalidCredentialsError
from swen_identity.services import JWTService, PasswordHashingService

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class LoginCommand:
    """Authenticate a user, tracking failed attempts even on failure."""

    def __init__(self, auth_service: AuthenticationService, uow: UnitOfWork):
        self._auth_service = auth_service
        self._uow = uow

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        jwt_service: JWTService,
        password_service: PasswordHashingService,
    ) -> LoginCommand:
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
        # InvalidCredentialsError/AccountLockedError are expected outcomes whose
        # side effects (failed-attempt counter, lockout) must still be committed,
        # not rolled back. So we have to make a workaround where we catch the
        # exception, commit the db transaction and then reraise it in the router
        async with self._uow:
            try:
                return await self._auth_service.login(email=email, password=password)
            except (InvalidCredentialsError, AccountLockedError) as e:
                caught = e

        raise caught
