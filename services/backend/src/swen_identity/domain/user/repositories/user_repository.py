"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, Union
from uuid import UUID

from swen_identity.domain.user.aggregates.user import User
from swen_identity.domain.user.value_objects.email import Email


class UserRepository(ABC):
    """Repository interface for User aggregates."""

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find a user by their ID."""

    @abstractmethod
    async def find_by_email(self, email: Union[str, Email]) -> Optional[User]:
        """Find a user by their email address."""

    @abstractmethod
    async def exists_by_email(self, email: Union[str, Email]) -> bool:
        """Check if a user exists with the given email."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Save or update a user."""

    @abstractmethod
    async def get_or_create_by_email(self, email: Union[str, Email]) -> User:
        """Get an existing user by email, or create a new one."""

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete a user by ID."""

    @abstractmethod
    async def delete_with_all_data(self, user_id: UUID) -> None:
        """Delete a user and all associated data."""

    @abstractmethod
    async def count(self) -> int:
        """Count total users."""

    @abstractmethod
    async def list_all(self) -> list[User]:
        """List all users."""
