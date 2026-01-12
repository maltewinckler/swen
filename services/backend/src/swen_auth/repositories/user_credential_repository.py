"""Abstract repository interface for user credentials.

This interface defines the contract for credential persistence.
Implementations can use SQLAlchemy, MongoDB, or any other storage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UserCredentialData:
    """Immutable credential data returned by repository.

    This is a pure data transfer object that decouples the domain
    from persistence implementation details.
    """

    user_id: str
    password_hash: str
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None


class UserCredentialRepository(ABC):
    """
    Abstract repository interface for user authentication credentials.

    Implementations must provide methods for:
    - Saving/updating credentials
    - Finding credentials by user ID
    - Managing failed login attempts and account lockout
    - Tracking last login

    Example implementation:
        class UserCredentialRepositorySQLAlchemy(UserCredentialRepository):
            def __init__(self, session: AsyncSession):
                self._session = session

            async def save(self, user_id: UUID, password_hash: str) -> None:
                # SQLAlchemy-specific implementation
                ...
    """

    # Default lockout settings (can be overridden by implementations)
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    @abstractmethod
    async def save(self, user_id: UUID, password_hash: str) -> UserCredentialData:
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

    @abstractmethod
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

    @abstractmethod
    async def increment_failed_attempts(self, user_id: UUID) -> int:
        """
        Increment failed login attempts for a user.

        Should automatically lock the account if max attempts exceeded.

        Parameters
        ----------
        user_id
            The user's unique identifier

        Returns
        -------
        The new count of failed attempts
        """

    @abstractmethod
    async def reset_failed_attempts(self, user_id: UUID) -> None:
        """
        Reset failed login attempts after successful login.

        Should also clear any account lockout.

        Parameters
        ----------
        user_id
            The user's unique identifier
        """

    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> None:
        """
        Update last login timestamp.

        Called after successful authentication.

        Parameters
        ----------
        user_id
            The user's unique identifier
        """

    @abstractmethod
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

    @abstractmethod
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
