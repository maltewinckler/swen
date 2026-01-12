"""Repository interface for bank accounts."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from swen.domain.banking.value_objects import BankAccount


class BankAccountRepository(ABC):
    """Repository for persisting bank accounts fetched from banks."""

    @abstractmethod
    async def save(self, bank_account: BankAccount) -> None:
        """
        Save or update a bank account.

        Parameters
        ----------
        bank_account
            The bank account to save
        """

    @abstractmethod
    async def find_by_iban(self, iban: str) -> Optional[BankAccount]:
        """
        Find a bank account by IBAN.

        Parameters
        ----------
        iban
            The IBAN to search for

        Returns
        -------
        Bank account or None if not found
        """

    @abstractmethod
    async def find_all(self) -> list[BankAccount]:
        """
        Find all bank accounts for the current user.

        Returns
        -------
        List of bank accounts
        """

    @abstractmethod
    async def find_by_blz(self, blz: str) -> list[BankAccount]:
        """
        Find all bank accounts for a specific bank (by BLZ/bank code).

        Parameters
        ----------
        blz
            The bank code (Bankleitzahl)

        Returns
        -------
        List of bank accounts for that bank
        """

    @abstractmethod
    async def delete(self, iban: str) -> None:
        """
        Delete a bank account.

        Parameters
        ----------
        iban
            The IBAN of the account to delete
        """

    @abstractmethod
    async def update_last_sync(self, iban: str, sync_time: datetime) -> None:
        """
        Update the last sync timestamp for an account.

        Parameters
        ----------
        iban
            The IBAN of the account
        sync_time
            The timestamp of the sync
        """
