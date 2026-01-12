"""Database integrity port. Interface for integrity operations."""

from typing import Protocol


class DatabaseIntegrityPort(Protocol):
    """Port for database integrity read/write operations.

    Implementations should handle the low-level database operations
    needed for integrity checks and repairs.
    """

    async def find_orphan_transaction_ids(
        self,
        *,
        opening_balance_metadata_key: str,
        source_metadata_key: str,
    ) -> tuple[str, ...]:
        """Find accounting transaction IDs without import records.

        Excludes transactions marked as opening balance or manual.

        Parameters
        ----------
        opening_balance_metadata_key
            The metadata key for is_opening_balance flag
        source_metadata_key
            The metadata key for source field

        Returns
        -------
        Tuple of transaction IDs (as strings)
        """
        ...

    async def find_duplicate_transaction_ids(self) -> tuple[str, ...]:
        """Find duplicate transactions (same date, description, amount).

        Returns
        -------
        Tuple of transaction IDs (as strings) that are duplicates
        """
        ...

    async def find_orphan_import_ids(self) -> tuple[str, ...]:
        """Find import record IDs pointing to non-existent transactions.

        Returns
        -------
        Tuple of import record IDs (as strings)
        """
        ...

    async def find_unbalanced_transaction_ids(self) -> tuple[str, ...]:
        """Find transaction IDs where debits don't equal credits.

        Returns
        -------
        Tuple of transaction IDs (as strings)
        """
        ...

    async def delete_transactions_with_entries(
        self,
        transaction_ids: tuple[str, ...],
    ) -> int:
        """Delete transactions and their journal entries.

        Parameters
        ----------
        transaction_ids
            Tuple of transaction IDs to delete

        Returns
        -------
        Number of transactions deleted
        """
        ...

    async def delete_import_records(
        self,
        import_ids: tuple[str, ...],
    ) -> int:
        """Delete orphan import records.

        Parameters
        ----------
        import_ids
            Tuple of import record IDs to delete

        Returns
        -------
        Number of import records deleted
        """
        ...
