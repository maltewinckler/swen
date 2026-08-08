from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.domain import (
    CannotDeleteSelfError,
    UserNotFoundError,
    UserRepository,
)

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class DeleteUserCommand:
    """Command to delete a user."""

    def __init__(self, user_repository: UserRepository, uow: UnitOfWork):
        self._user_repo = user_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeleteUserCommand:
        return cls(
            user_repository=factory.user_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, user_id: UUID, requesting_admin_id: UUID) -> None:
        if user_id == requesting_admin_id:
            raise CannotDeleteSelfError

        async with self._uow:
            user = await self._user_repo.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(str(user_id))

            await self._user_repo.delete_with_all_data(user_id)
