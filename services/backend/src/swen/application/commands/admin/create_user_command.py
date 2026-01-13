from swen.domain.user import EmailAlreadyExistsError, User, UserRepository, UserRole
from swen_auth.repositories import UserCredentialRepository
from swen_auth.services import PasswordHashingService


class CreateUserCommand:
    """Command to create a new user."""

    def __init__(
        self,
        user_repository: UserRepository,
        credential_repository: UserCredentialRepository,
        password_service: PasswordHashingService,
    ):
        self._user_repo = user_repository
        self._credential_repo = credential_repository
        self._password_service = password_service

    async def execute(
        self,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        existing = await self._user_repo.find_by_email(email)
        if existing:
            raise EmailAlreadyExistsError(email)

        user = User.create(email, role=role)
        password_hash = self._password_service.hash(password)

        await self._user_repo.save(user)
        await self._credential_repo.save(user_id=user.id, password_hash=password_hash)

        return user
