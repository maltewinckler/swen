"""Repository interface for transaction imports."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.value_objects import ImportStatus


class TransactionImportRepository(ABC):
    """Repository interface for persisting and retrieving transaction imports."""

    @abstractmethod
    async def save(self, transaction_import: TransactionImport) -> None:
        """
        Save a transaction import record.

        Parameters
        ----------
        transaction_import
            Transaction import to save
        """

    @abstractmethod
    async def find_by_id(self, import_id: UUID) -> Optional[TransactionImport]:
        """
        Find a transaction import by ID.

        Parameters
        ----------
        import_id
            Import ID to search for

        Returns
        -------
        Transaction import if found, None otherwise
        """

    @abstractmethod
    async def find_by_bank_transaction_id(
        self,
        bank_transaction_id: UUID,
    ) -> Optional[TransactionImport]:
        """
        Find a transaction import by stored bank transaction ID.

        This is the primary method for duplicate detection.

        Parameters
        ----------
        bank_transaction_id
            UUID of the stored bank transaction

        Returns
        -------
        Transaction import if found, None otherwise
        """

    @abstractmethod
    async def find_by_accounting_transaction_id(
        self,
        transaction_id: UUID,
    ) -> Optional[TransactionImport]:
        """
        Find import record by accounting transaction ID.

        Useful for audit trail (find source bank transaction for accounting entry).

        Parameters
        ----------
        transaction_id
            Accounting transaction ID

        Returns
        -------
        Transaction import if found, None otherwise
        """

    @abstractmethod
    async def find_by_status(self, status: ImportStatus) -> List[TransactionImport]:
        """
        Find all imports with a specific status.

        Parameters
        ----------
        status
            Import status to filter by

        Returns
        -------
        List of matching imports (may be empty)
        """

    @abstractmethod
    async def find_by_iban(self, iban: str) -> List[TransactionImport]:
        """
        Find all imports for a specific bank account.

        Parameters
        ----------
        iban
            Bank account IBAN

        Returns
        -------
        List of imports for this account (may be empty)
        """

    @abstractmethod
    async def find_failed_imports(
        self,
        since: Optional[datetime] = None,
    ) -> List[TransactionImport]:
        """
        Find all failed imports, optionally filtered by date.

        Useful for retry operations.

        Parameters
        ----------
        since
            Only return failures since this timestamp (optional)

        Returns
        -------
        List of failed imports (may be empty)
        """

    @abstractmethod
    async def find_imports_in_date_range(
        self,
        iban: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[TransactionImport]:
        """
        Find all imports for an account within a date range.

        Parameters
        ----------
        iban
            Bank account IBAN
        start_date
            Start of date range
        end_date
            End of date range

        Returns
        -------
        List of imports in range (may be empty)
        """

    @abstractmethod
    async def count_by_status(self, iban: Optional[str] = None) -> dict[str, int]:
        """
        Count imports by status, optionally filtered by IBAN.

        Parameters
        ----------
        iban
            Bank account IBAN (optional)

        Returns
        -------
        Dictionary mapping status name to count
        Example
            {"success": 150, "failed": 5, "duplicate": 3}
        """

    @abstractmethod
    async def delete(self, import_id: UUID) -> bool:
        """
        Delete a transaction import record.

        Parameters
        ----------
        import_id
            Import ID to delete

        Returns
        -------
        True if deleted, False if not found
        """
