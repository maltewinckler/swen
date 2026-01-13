"""Authentication service for user registration and login."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.user import EmailAlreadyExistsError, User, UserRole
from swen_auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    JWTService,
    PasswordHashingService,
    TokenPayload,
)
from swen_auth.repositories import UserCredentialRepository

if TYPE_CHECKING:
    from swen.domain.user import UserRepository

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Application service for user authentication.

    Orchestrates swen_auth infrastructure (password hashing, JWT tokens)
    with the swen User domain to provide:
    - User registration
    - Login with password
    - Token refresh
    - Password change

    This service is the bridge between the generic auth infrastructure
    and the domain-specific User aggregate.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        credential_repository: UserCredentialRepository,
        password_service: PasswordHashingService,
        jwt_service: JWTService,
    ):
        self._user_repo = user_repository
        self._credential_repo = credential_repository
        self._password_service = password_service
        self._jwt_service = jwt_service

    def _create_token_pair(self, user: User) -> tuple[str, str]:
        access_token = self._jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
        )
        refresh_token = self._jwt_service.create_refresh_token(
            user_id=user.id,
            email=user.email,
        )
        return access_token, refresh_token

    async def register(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        existing_user = await self._user_repo.find_by_email(email)
        if existing_user is not None:
            raise EmailAlreadyExistsError(email)

        # First user becomes admin
        user_count = await self._user_repo.count()
        role = UserRole.ADMIN if user_count == 0 else UserRole.USER

        password_hash = self._password_service.hash(password)
        user = User.create(email, role=role)
        await self._user_repo.save(user)
        await self._credential_repo.save(user_id=user.id, password_hash=password_hash)

        access_token, refresh_token = self._create_token_pair(user)

        logger.info("User registered: %s (role: %s)", email, role.value)
        return user, access_token, refresh_token

    async def login(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        user = await self._user_repo.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError

        is_locked, locked_until = await self._credential_repo.is_account_locked(
            user.id,
        )
        if is_locked:
            locked_until_str = locked_until.isoformat() if locked_until else "unknown"
            raise AccountLockedError(locked_until=locked_until_str)

        credential = await self._credential_repo.find_by_user_id(user.id)
        if credential is None:
            raise InvalidCredentialsError

        if not self._password_service.verify(password, credential.password_hash):
            await self._credential_repo.increment_failed_attempts(user.id)
            raise InvalidCredentialsError

        await self._credential_repo.reset_failed_attempts(user.id)
        await self._credential_repo.update_last_login(user.id)

        access_token, refresh_token = self._create_token_pair(user)

        logger.info("User logged in: %s", email)
        return user, access_token, refresh_token

    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        payload = self._jwt_service.verify_token(refresh_token)

        if not payload.is_refresh_token():
            msg = "Not a refresh token"
            raise InvalidTokenError(msg)
        user = await self._user_repo.find_by_id(payload.user_id)
        if user is None:
            msg = "User not found"
            raise InvalidTokenError(msg)

        new_access_token, new_refresh_token = self._create_token_pair(user)

        logger.debug("Tokens refreshed for user: %s", user.email)
        return new_access_token, new_refresh_token

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ):
        credential = await self._credential_repo.find_by_user_id(user_id)
        if credential is None:
            msg = "User credentials not found"
            raise InvalidCredentialsError(msg)
        if not self._password_service.verify(
            current_password,
            credential.password_hash,
        ):
            msg = "Current password is incorrect"
            raise InvalidCredentialsError(msg)

        new_hash = self._password_service.hash(new_password)
        await self._credential_repo.save(user_id=user_id, password_hash=new_hash)

        logger.info("Password changed for user: %s", user_id)

    def verify_token(self, token: str) -> TokenPayload:
        return self._jwt_service.verify_token(token)
