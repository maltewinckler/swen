"""Transaction repository interface.

Defines the contract for Transaction persistence. Implementations are
user-scoped via UserContext, meaning all queries automatically
filter by the current user's user_id.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction


class TransactionRepository(ABC):
    """
    Repository interface for Transaction aggregates.

    Note: Implementations are scoped to a specific user via UserContext.
    All queries automatically filter by the context's user_id.
    Callers don't need to pass user_id explicitly.
    """

    @abstractmethod
    async def save(self, transaction: Transaction) -> None:
        """Save a transaction."""

    @abstractmethod
    async def find_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """Find transaction by ID."""

    @abstractmethod
    async def find_by_account(self, account_id: UUID) -> List[Transaction]:
        """Find all transactions involving an account."""

    @abstractmethod
    async def find_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Transaction]:
        """Find transactions within a date range."""

    @abstractmethod
    async def find_all(self) -> List[Transaction]:
        """Find all transactions (both draft and posted)."""

    @abstractmethod
    async def find_posted_transactions(self) -> List[Transaction]:
        """Find all posted transactions."""

    @abstractmethod
    async def find_draft_transactions(self) -> List[Transaction]:
        """Find all draft transactions."""

    @abstractmethod
    async def delete(self, transaction_id: UUID) -> None:
        """Delete a transaction."""

    @abstractmethod
    async def find_by_counterparty(self, counterparty: str) -> List[Transaction]:
        """Find all transactions with a specific counterparty name."""

    @abstractmethod
    async def find_by_counterparty_iban(
        self,
        counterparty_iban: str,
    ) -> List[Transaction]:
        """Find transactions by counterparty IBAN."""

    @abstractmethod
    async def find_by_metadata(
        self,
        metadata_key: str,
        metadata_value: Optional[Any] = None,
    ) -> List[Transaction]:
        """Find transactions by metadata tag."""

    @abstractmethod
    async def find_by_account_and_counterparty(
        self,
        account_id: UUID,
        counterparty: str,
    ) -> List[Transaction]:
        """Find transactions involving a specific account and counterparty."""

    @abstractmethod
    async def find_with_filters(  # NOQA: PLR0913
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        account_id: Optional[UUID] = None,
        exclude_internal_transfers: bool = False,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Transaction]:
        """
        Find transactions with multiple filters applied at SQL level.

        This is more efficient than loading all transactions and filtering in Python.

        Parameters
        ----------
        start_date
            Filter transactions on or after this date (ISO format)
        end_date
            Filter transactions on or before this date (ISO format)
        status
            Filter by status: 'posted', 'draft', or None for all
        account_id
            Filter to transactions involving this account
        exclude_internal_transfers
            If True, exclude internal transfers between own accounts
        source_filter
            Filter by source: 'bank_import', 'manual', etc.
        limit
            Maximum number of transactions to return

        Returns
        -------
        List of transactions matching the filters, sorted by date descending
        """

    @abstractmethod
    async def count_by_status(self) -> dict[str, int]:
        """Count transactions by status (posted vs draft)."""
