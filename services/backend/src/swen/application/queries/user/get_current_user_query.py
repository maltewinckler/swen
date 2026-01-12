"""Query to get the current user and their preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from swen.domain.user import Email, User, UserRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class GetCurrentUserQuery:
    """Query to retrieve the current user by email."""

    def __init__(
        self,
        user_repo: UserRepository,
        email: Optional[str] = None,
    ) -> None:
        self._user_repo = user_repo
        self._email = email

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> GetCurrentUserQuery:
        return cls(
            user_repo=factory.user_repository(),
            email=factory.user_context.email,
        )

    async def execute(self, email: Optional[Union[str, Email]] = None) -> User:
        resolved_email = email or self._email
        if not resolved_email:
            msg = "Email must be provided either at construction or execution"
            raise ValueError(msg)
        return await self._user_repo.get_or_create_by_email(resolved_email)
