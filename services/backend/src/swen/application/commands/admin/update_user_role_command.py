from uuid import UUID

from swen.domain.user import (
    CannotDemoteSelfError,
    User,
    UserNotFoundError,
    UserRepository,
    UserRole,
)


class UpdateUserRoleCommand:
    """Command to update a user's role."""

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository

    async def execute(
        self,
        user_id: UUID,
        new_role: UserRole,
        requesting_admin_id: UUID,
    ) -> User:
        if user_id == requesting_admin_id and new_role != UserRole.ADMIN:
            raise CannotDemoteSelfError

        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        if new_role == UserRole.ADMIN:
            user.promote_to_admin()
        else:
            user.demote_to_user()

        await self._user_repo.save(user)
        return user
