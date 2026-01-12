"""Account repository interface.

Defines the contract for Account persistence. Implementations are
user-scoped via UserContext, meaning all queries automatically
filter by the current user's user_id.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from swen.domain.accounting.entities import Account


class AccountRepository(ABC):
    """
    Repository interface for Account entities.

    Note: Implementations are scoped to a specific user via UserContext.
    All queries automatically filter by the context's user_id.
    Callers don't need to pass user_id explicitly.
    """

    @abstractmethod
    async def save(self, account: Account) -> None:
        """Save an account for the current user."""

    @abstractmethod
    async def find_by_id(self, account_id: UUID) -> Optional[Account]:
        """Find account by ID."""

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Account]:
        """Find account by name."""

    @abstractmethod
    async def find_by_account_number(self, account_number: str) -> Optional[Account]:
        """Find account by account number."""

    @abstractmethod
    async def find_by_iban(self, iban: str) -> Optional[Account]:
        """Find account by IBAN."""

    @abstractmethod
    async def find_all_active(self) -> List[Account]:
        """Find all active accounts."""

    @abstractmethod
    async def find_all(self) -> List[Account]:
        """Find all accounts (including inactive)."""

    @abstractmethod
    async def find_by_type(self, account_type: str) -> List[Account]:
        """Find accounts by type."""

    @abstractmethod
    async def delete(self, account_id: UUID) -> None:
        """Delete an account."""

    @abstractmethod
    async def find_children(self, parent_id: UUID) -> List[Account]:
        """Find all direct children of a parent account."""

    @abstractmethod
    async def find_descendants(self, parent_id: UUID) -> List[Account]:
        """Find all descendants (recursive!) of a parent account."""

    @abstractmethod
    async def find_by_parent_id(self, parent_id: UUID) -> List[Account]:
        """Alias for find_children for clarity."""

    @abstractmethod
    async def is_parent(self, account_id: UUID) -> bool:
        """Check if account has any children."""

    @abstractmethod
    async def get_hierarchy_path(self, account_id: UUID) -> List[Account]:
        """Get full path from root to this account (e.g., [Expenses, dood, bars])."""
