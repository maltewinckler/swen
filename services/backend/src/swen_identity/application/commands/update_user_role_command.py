from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen_identity.application.ports.unit_of_work import UnitOfWork
from swen_identity.domain.user import (
    CannotDemoteSelfError,
    User,
    UserNotFoundError,
    UserRepository,
    UserRole,
)

if TYPE_CHECKING:
    from swen_identity.application.factories import RepositoryFactory


class UpdateUserRoleCommand:
    """Command to update a user's role."""

    def __init__(self, user_repository: UserRepository, uow: UnitOfWork):
        self._user_repo = user_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateUserRoleCommand:
        return cls(
            user_repository=factory.user_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(
        self,
        user_id: UUID,
        new_role: UserRole,
        requesting_admin_id: UUID,
    ) -> User:
        if user_id == requesting_admin_id and new_role != UserRole.ADMIN:
            raise CannotDemoteSelfError

        async with self._uow:
            user = await self._user_repo.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(str(user_id))

            if new_role == UserRole.ADMIN:
                user.promote_to_admin()
            else:
                user.demote_to_user()

            await self._user_repo.save(user)
            return user
