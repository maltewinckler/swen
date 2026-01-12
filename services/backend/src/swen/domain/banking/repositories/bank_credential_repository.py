"""Bank credential repository interface - Banking domain.

CRITICAL: This interface is defined in the BANKING DOMAIN.
Why? Because Banking needs credentials, so Banking defines the contract.

The implementation (in Infrastructure) will use the Security domain
to retrieve encrypted data, decrypt it, and return BankCredentials.

This follows Dependency Inversion Principle:
- High-level (Banking) defines the interface
- Low-level (Infrastructure) implements it
"""

from abc import ABC, abstractmethod
from typing import Optional

from swen.domain.banking.value_objects import BankCredentials


class BankCredentialRepository(ABC):
    """Repository for bank credentials - defined by Banking domain needs."""

    @abstractmethod
    async def save(
        self,
        credentials: BankCredentials,
        label: Optional[str] = None,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
    ) -> str:
        """Store bank credentials.

        Parameters
        ----------
        credentials
            BankCredentials value object to store
        label
            Optional user-friendly label (e.g., "Main DKB Account")
        tan_method
            Optional TAN method code (e.g., "946" for SecureGo plus)
        tan_medium
            Optional TAN medium/device name (e.g., "SecureGo")

        Returns
        -------
        Unique identifier for the stored credentials

        Raises
        ------
        ValueError
            If credentials already exist for this user+blz
        """

    @abstractmethod
    async def find_by_blz(self, blz: str) -> Optional[BankCredentials]:
        """Retrieve credentials by bank code.

        Parameters
        ----------
        blz
            Bankleitzahl (8-digit bank code)

        Returns
        -------
        BankCredentials or None
        """

    @abstractmethod
    async def find_all(self) -> list[tuple[str, str, str]]:
        """
        List all stored credentials for the current user (metadata only).

        Returns non-sensitive information for displaying to user.
        Must NOT decrypt or return actual credentials!!

        Returns
        -------
        List of (credential_id, blz, label) tuples
        """

    @abstractmethod
    async def delete(self, blz: str) -> bool:
        """
        Delete stored credentials for the current user.

        Parameters
        ----------
        blz
            Bankleitzahl to delete

        Returns
        -------
        True if deleted, False if not found
        """

    @abstractmethod
    async def update_last_used(
        self,
        blz: str,
    ) -> None:
        """
        Update last used timestamp for audit trail.

        Called after successfully using credentials for sync.

        Parameters
        ----------
        blz
            Bankleitzahl that was used
        """

    @abstractmethod
    async def get_tan_settings(
        self,
        blz: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Get TAN settings for a bank (current user).

        Parameters
        ----------
        blz
            Bankleitzahl

        Returns
        -------
        Tuple of (tan_method, tan_medium)
        """
