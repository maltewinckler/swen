"""SQLAlchemy implementation of UserCredentialRepository.

Provides data access for UserCredentialModel with security-focused
operations like account lockout management.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen_auth.persistence.sqlalchemy.models import UserCredentialModel
from swen_auth.repositories import UserCredentialData, UserCredentialRepository

logger = logging.getLogger(__name__)


class UserCredentialRepositorySQLAlchemy(UserCredentialRepository):
    """
    SQLAlchemy implementation of UserCredentialRepository.

    Provides CRUD operations plus security-specific methods for
    account lockout management using SQLAlchemy as the ORM.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Parameters
        ----------
        session
            SQLAlchemy async session
        """
        self._session = session

    def _to_data(self, model: UserCredentialModel) -> UserCredentialData:
        """Map SQLAlchemy model to domain data transfer object."""
        return UserCredentialData(
            user_id=model.user_id,
            password_hash=model.password_hash,
            failed_login_attempts=model.failed_login_attempts,
            locked_until=model.locked_until,
            last_login_at=model.last_login_at,
        )

    async def _find_model_by_user_id(self, user_id: UUID) -> UserCredentialModel | None:
        """Internal helper to find the concrete model for modification."""
        user_id_str = str(user_id)
        stmt = select(UserCredentialModel).where(
            UserCredentialModel.user_id == user_id_str,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> UserCredentialData:
        """
        Create or update credentials for a user.

        Parameters
        ----------
        user_id
            The user's unique identifier
        password_hash
            The bcrypt password hash

        Returns
        -------
        The saved credential data
        """
        # Check if credential exists
        existing = await self._find_model_by_user_id(user_id)

        if existing:
            # Update existing
            existing.password_hash = password_hash
            existing.updated_at = datetime.now(tz=timezone.utc)
            logger.debug("Updated credentials for user: %s", user_id)
            await self._session.flush()
            return self._to_data(existing)

        # Create new - store user_id as string
        model = UserCredentialModel(
            user_id=str(user_id),
            password_hash=password_hash,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("Created credentials for user: %s", user_id)
        return self._to_data(model)

    async def find_by_user_id(self, user_id: UUID) -> UserCredentialData | None:
        """
        Find credentials by user ID.

        Parameters
        ----------
        user_id
            The user's unique identifier

        Returns
        -------
        Credential data if found, None otherwise
        """
        model = await self._find_model_by_user_id(user_id)
        return self._to_data(model) if model else None

    async def increment_failed_attempts(self, user_id: UUID) -> int:
        """
        Increment failed login attempts for a user.

        Automatically locks the account if max attempts exceeded.

        Parameters
        ----------
        user_id
            The user's unique identifier

        Returns
        -------
        The new count of failed attempts
        """
        credential = await self._find_model_by_user_id(user_id)
        if not credential:
            return 0

        credential.failed_login_attempts += 1
        credential.updated_at = datetime.now(tz=timezone.utc)

        # Lock account if too many failed attempts
        if credential.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
            credential.locked_until = datetime.now(tz=timezone.utc) + timedelta(
                minutes=self.LOCKOUT_DURATION_MINUTES,
            )
            logger.warning(
                "Account locked for user %s due to %d failed attempts",
                user_id,
                credential.failed_login_attempts,
            )

        await self._session.flush()
        return credential.failed_login_attempts

    async def reset_failed_attempts(self, user_id: UUID) -> None:
        """
        Reset failed login attempts after successful login.

        Also clears any account lockout.

        Parameters
        ----------
        user_id
            The user's unique identifier
        """
        credential = await self._find_model_by_user_id(user_id)
        if credential:
            credential.failed_login_attempts = 0
            credential.locked_until = None
            credential.updated_at = datetime.now(tz=timezone.utc)
            await self._session.flush()

    async def update_last_login(self, user_id: UUID) -> None:
        """
        Update last login timestamp.

        Called after successful authentication.

        Parameters
        ----------
        user_id
            The user's unique identifier
        """
        credential = await self._find_model_by_user_id(user_id)
        if credential:
            credential.last_login_at = datetime.now(tz=timezone.utc)
            credential.updated_at = datetime.now(tz=timezone.utc)
            await self._session.flush()

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete credentials for a user.

        Parameters
        ----------
        user_id
            The user's unique identifier

        Returns
        -------
        True if deleted, False if not found
        """
        credential = await self._find_model_by_user_id(user_id)
        if credential:
            await self._session.delete(credential)
            await self._session.flush()
            logger.info("Deleted credentials for user: %s", user_id)
            return True
        return False

    async def is_account_locked(self, user_id: UUID) -> tuple[bool, datetime | None]:
        """
        Check if an account is locked.

        Parameters
        ----------
        user_id
            The user's unique identifier

        Returns
        -------
        Tuple of (is_locked, locked_until) where locked_until is None
        if not locked
        """
        credential = await self._find_model_by_user_id(user_id)
        if not credential:
            return False, None

        now = datetime.now(tz=timezone.utc)
        if credential.locked_until and credential.locked_until > now:
            return True, credential.locked_until

        return False, None
