"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, Union
from uuid import UUID

from swen.domain.user.aggregates.user import User
from swen.domain.user.value_objects.email import Email


class UserRepository(ABC):
    """Repository interface for User aggregates."""

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Find a user by their ID.

        Parameters
        ----------
        user_id
            The user's unique identifier (UUID4)

        Returns
        -------
        User if found, None otherwise
        """

    @abstractmethod
    async def find_by_email(self, email: Union[str, Email]) -> Optional[User]:
        """
        Find a user by their email address.

        Performs a database query on the email column.

        Parameters
        ----------
        email
            The user's email address (string or Email value object)

        Returns
        -------
        User if found, None otherwise

        Raises
        ------
        InvalidEmailError
            If email format is invalid
        """

    @abstractmethod
    async def exists_by_email(self, email: Union[str, Email]) -> bool:
        """
        Check if a user exists with the given email.

        Parameters
        ----------
        email
            The email address to check

        Returns
        -------
        True if user exists, False otherwise

        Raises
        ------
        InvalidEmailError
            If email format is invalid
        """

    @abstractmethod
    async def save(self, user: User) -> None:
        """
        Save or update a user.

        If the user exists (by ID), updates it.
        If the user doesn't exist, creates it.

        Parameters
        ----------
        user
            The user to save

        Raises
        ------
        EmailAlreadyExistsError
            If email is already in use by another user
        """

    @abstractmethod
    async def get_or_create_by_email(self, email: Union[str, Email]) -> User:
        """
        Get an existing user by email, or create a new one.

        This is the primary method for user authentication/identification:
        1. Queries database for user with this email
        2. If not found, creates a new user with random ID and default preferences
        3. Returns the user

        Parameters
        ----------
        email
            User's email address

        Returns
        -------
        Existing or newly created User

        Raises
        ------
        InvalidEmailError
            If email format is invalid
        """

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """
        Delete a user by ID.

        Note: In the current implementation, this only deletes the user record.
        For cascade deletion of all user data, use delete_with_all_data().

        Parameters
        ----------
        user_id
            The user's unique identifier
        """

    @abstractmethod
    async def delete_with_all_data(self, user_id: UUID) -> None:
        """
        Delete a user and ALL associated data.

        This method removes:
        - User record and preferences
        - Bank credentials
        - Bank accounts and transactions
        - Accounting accounts and transactions
        - Account mappings
        - Import history
        - Categorization rules

        Used for GDPR/data protection compliance.

        Parameters
        ----------
        user_id
            The user's unique identifier
        """
