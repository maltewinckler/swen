"""Bank connection port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

if TYPE_CHECKING:
    from swen.domain.banking.value_objects.bank_account import BankAccount
    from swen.domain.banking.value_objects.bank_credentials import BankCredentials
    from swen.domain.banking.value_objects.bank_transaction import BankTransaction
    from swen.domain.banking.value_objects.tan_challenge import TANChallenge
    from swen.domain.banking.value_objects.tan_method import TANMethod


class BankConnectionPort(ABC):
    """
    Interface for bank connections.

    This defines what our domain needs from banks online services
    (e.g. FinTS/HBCI or PSD2).
    """

    @abstractmethod
    async def connect(self, credentials: BankCredentials) -> bool:
        """
        Establish connection to the bank.

        Parameters
        ----------
        credentials
            Bank credentials for authentication

        Returns
        -------
        True if connection successful, False otherwise

        Raises
        ------
        BankConnectionError
            If connection fails
        """

    @abstractmethod
    async def fetch_accounts(self) -> list[BankAccount]:
        """
        Fetch all accounts accessible with current credentials.

        Returns
        -------
        List of bank accounts

        Raises
        ------
        BankConnectionError
            If not connected or fetch fails
        """

    @abstractmethod
    async def fetch_transactions(
        self,
        account_iban: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[BankTransaction]:
        """
        Fetch transactions for a specific account.

        Parameters
        ----------
        account_iban
            IBAN of the account
        start_date
            Start date for transaction history
        end_date
            End date for transaction history (defaults to today)

        Returns
        -------
        List of bank transactions in domain format

        Raises
        ------
        BankConnectionError
            If not connected or fetch fails
        ValueError
            If account not found
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the bank connection and cleanup resources."""

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to bank.

        Returns
        -------
        True if connected, False otherwise
        """

    @abstractmethod
    async def set_tan_callback(
        self,
        callback: Callable[[TANChallenge], Awaitable[str]],
    ) -> None:
        """
        Set callback function for TAN (Transaction Authentication Number) input.

        TAN authentication may be required by the bank for security-sensitive
        read operations such as:
        - Initial login/connection
        - Fetching long transaction histories
        - Accessing certain account details

        Parameters
        ----------
        callback
            Async function that receives TANChallenge and returns the TAN entered
            by the user

        Examples
        --------
        async def tan_callback(challenge: TANChallenge) -> str:
            print(f"Challenge: {challenge.challenge_text}")
            return input("Enter TAN: ")

        await adapter.set_tan_callback(tan_callback)
        """

    @abstractmethod
    def set_tan_method(self, tan_method: str) -> None:
        """
        Set the preferred TAN method for authentication.

        Must be called before connect() to take effect.

        Parameters
        ----------
        tan_method
            TAN method code (e.g., "946" for SecureGo plus, "962" for manual, "972"
            for optical, "982" for photo)
        """

    @abstractmethod
    def set_tan_medium(self, tan_medium: str) -> None:
        """
        Set the TAN medium/device name.

        Must be called before connect() to take effect.

        Parameters
        ----------
        tan_medium
            Device name (e.g., "SecureGo")
        """

    @abstractmethod
    async def get_tan_methods(
        self,
        credentials: BankCredentials,
    ) -> list[TANMethod]:
        """
        Get available TAN methods from the bank.

        This queries the bank's BPD (Bank Parameter Data) to discover
        which TAN authentication methods are supported for the user.

        Note: This typically uses a sync dialog that does NOT require
        TAN approval, making it safe to call before choosing a TAN method.

        This method can be called without an active connection - it will
        establish a temporary connection to query the methods.

        Parameters
        ----------
        credentials
            Bank credentials to authenticate with

        Returns
        -------
        List of available TAN methods

        Raises
        ------
        BankConnectionError
            If query fails
        """
