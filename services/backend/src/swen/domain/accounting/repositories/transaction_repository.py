"""Transaction repository interface.

Defines the contract for Transaction persistence. Implementations are
user-scoped via UserContext, meaning all queries automatically
filter by the current user's user_id.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from uuid import UUID

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.value_objects import TransactionFilters
from swen.domain.shared.value_objects import Pagination


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
    async def find_with_filters(
        self,
        filters: TransactionFilters,
        pagination: Optional[Pagination] = None,
    ) -> List[Transaction]:
        """
        Find transactions with filters and optional pagination.

        Parameters
        ----------
        filters
            Filtering criteria (date range, status, account, etc.)
        pagination
            Page-based pagination. If None, returns all matching results.

        Returns
        -------
        List of transactions matching the filters, sorted by date descending.
        """

    @abstractmethod
    async def count_with_filters(
        self,
        filters: TransactionFilters,
    ) -> int:
        """
        Count transactions matching the given filters.

        Useful for computing total pages in paginated responses.
        """

    @abstractmethod
    async def count_by_status(self) -> dict[str, int]:
        """Count transactions by status (posted vs draft)."""
