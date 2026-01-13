from uuid import UUID

from swen.domain.user import CannotDeleteSelfError, UserNotFoundError, UserRepository


class DeleteUserCommand:
    """Command to delete a user."""

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository

    async def execute(self, user_id: UUID, requesting_admin_id: UUID) -> None:
        if user_id == requesting_admin_id:
            raise CannotDeleteSelfError

        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        await self._user_repo.delete_with_all_data(user_id)
