"""Repository interface for bank transactions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from swen.domain.banking.value_objects import BankTransaction


@dataclass
class StoredBankTransaction:
    """A bank transaction record as stored in the database.

    This is returned by save operations to provide the caller with
    the database ID and import status of each transaction.
    """

    id: UUID
    identity_hash: str
    hash_sequence: int
    transaction: BankTransaction
    is_imported: bool
    is_new: bool


class BankTransactionRepository(ABC):
    """Repository for persisting bank transactions."""

    @abstractmethod
    async def save_batch_with_deduplication(
        self,
        transactions: list[BankTransaction],
        account_iban: str,
    ) -> list[StoredBankTransaction]:
        """
        Save batch with hash + sequence deduplication.

        For each transaction:
        1. Compute identity hash
        2. Assign sequence number (1st occurrence = 1, 2nd = 2, etc.)
        3. Check if (hash, sequence) already exists
        4. Save new ones, return existing ones

        For the principle how to do it see docs/deduplication_logic.md.
        This is a crucial concept!!!

        Parameters
        ----------
        transactions
            List of bank transactions from the bank API
        account_iban
            IBAN of the account these belong to

        Returns
        -------
        List of StoredBankTransaction with DB IDs and status
        """

    @abstractmethod
    async def save(self, transaction: BankTransaction, account_iban: str) -> UUID:
        """
        Save a bank transaction and return its ID.

        Parameters
        ----------
        transaction
            The transaction to save
        account_iban
            The IBAN of the account this transaction belongs to

        Returns
        -------
        The UUID of the saved transaction

        Raises
        ------
        ValueError
            If account with given IBAN not found
        """

    @abstractmethod
    async def save_batch(
        self,
        transactions: list[BankTransaction],
        account_iban: str,
    ) -> list[UUID]:
        """
        Save multiple transactions efficiently.

        Parameters
        ----------
        transactions
            List of transactions to save
        account_iban
            The IBAN of the account these transactions belong to

        Returns
        -------
        List of UUIDs for the saved transactions
        """

    @abstractmethod
    async def find_by_id(self, transaction_id: UUID) -> Optional[BankTransaction]:
        """
        Find a transaction by ID.

        Parameters
        ----------
        transaction_id
            The UUID of the transaction

        Returns
        -------
        Bank transaction if found, None otherwise
        """

    @abstractmethod
    async def find_by_account(
        self,
        account_iban: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BankTransaction]:
        """
        Find all transactions for an account within date range.

        Parameters
        ----------
        account_iban
            The IBAN of the account
        start_date
            Start date for filtering (inclusive)
        end_date
            End date for filtering (inclusive)

        Returns
        -------
        List of bank transactions
        """

    @abstractmethod
    async def exists(self, account_iban: str, bank_reference: str) -> bool:
        """
        Check if a transaction already exists (for deduplication).

        Parameters
        ----------
        account_iban
            The IBAN of the account
        bank_reference
            The bank's reference number for the transaction

        Returns
        -------
        True if transaction exists, False otherwise
        """

    @abstractmethod
    async def get_latest_transaction_date(
        self,
        account_iban: str,
    ) -> Optional[date]:
        """
        Get the most recent transaction date for incremental sync.

        Parameters
        ----------
        account_iban
            The IBAN of the account

        Returns
        -------
        The most recent booking date, or None if no transactions exist
        """

    @abstractmethod
    async def count_by_account(self, account_iban: str) -> int:
        """
        Count transactions for an account.

        Parameters
        ----------
        account_iban
            The IBAN of the account

        Returns
        -------
        Number of transactions
        """
