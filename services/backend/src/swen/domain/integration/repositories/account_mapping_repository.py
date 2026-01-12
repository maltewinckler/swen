"""Repository interface for account mappings.

Defines the contract for AccountMapping persistence. Implementations are
user-scoped via UserContext, meaning all queries automatically
filter by the current user's user_id.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from swen.domain.integration.entities import AccountMapping


class AccountMappingRepository(ABC):
    """Repository interface for persisting and retrieving account mappings."""

    @abstractmethod
    async def save(self, mapping: AccountMapping) -> None:
        """
        Save an account mapping.

        Parameters
        ----------
        mapping
            Account mapping to save
        """

    @abstractmethod
    async def find_by_id(self, mapping_id: UUID) -> Optional[AccountMapping]:
        """
        Find an account mapping by ID.

        Parameters
        ----------
        mapping_id
            Mapping ID to search for

        Returns
        -------
        Account mapping if found, None otherwise
        """

    @abstractmethod
    async def find_by_iban(self, iban: str) -> Optional[AccountMapping]:
        """
        Find an account mapping by IBAN.

        Parameters
        ----------
        iban
            Bank account IBAN to search for

        Returns
        -------
        Account mapping if found, None otherwise
        """

    @abstractmethod
    async def find_by_accounting_account_id(
        self,
        account_id: UUID,
    ) -> List[AccountMapping]:
        """
        Find all mappings for a given accounting account.

        Parameters
        ----------
        account_id
            Accounting account ID

        Returns
        -------
        List of mappings (may be empty)
        """

    @abstractmethod
    async def find_all_active(self) -> List[AccountMapping]:
        """
        Find all active account mappings.

        Returns
        -------
        List of active mappings (may be empty)
        """

    @abstractmethod
    async def find_all(self) -> List[AccountMapping]:
        """
        Find all account mappings (active and inactive).

        Returns
        -------
        List of all mappings (may be empty)
        """

    @abstractmethod
    async def delete(self, mapping_id: UUID) -> bool:
        """
        Delete an account mapping.

        Parameters
        ----------
        mapping_id
            Mapping ID to delete

        Returns
        -------
        True if deleted, False if not found
        """

    @abstractmethod
    async def exists_for_iban(self, iban: str) -> bool:
        """
        Check if a mapping exists for the given IBAN.

        Parameters
        ----------
        iban
            Bank account IBAN

        Returns
        -------
        True if mapping exists, False otherwise
        """
