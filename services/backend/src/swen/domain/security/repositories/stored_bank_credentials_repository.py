"""Repository interface for stored bank credentials - Security domain."""

from abc import ABC, abstractmethod
from typing import Optional

from swen.domain.security.entities import StoredBankCredentials


class StoredBankCredentialsRepository(ABC):
    """
    Repository for encrypted credential storage.

    This is a Security domain repository that deals with
    StoredBankCredentials entities.

    It does NOT:
    - Know about BankCredentials (Banking domain)
    - Perform decryption (that's EncryptionService's job)
    - Do domain translation (that's BankCredentialRepository's job)

    It ONLY:
    - Loads/saves encrypted credential records
    - Manages persistence of StoredBankCredentials entities
    """

    @abstractmethod
    async def save(
        self,
        stored_credentials: StoredBankCredentials,
    ) -> None:
        """
        Save encrypted credentials to storage for the current user.

        Parameters
        ----------
        stored_credentials
            StoredBankCredentials entity with encrypted fields

        Raises
        ------
        ValueError
            If credentials already exist for this user+blz
        """

    @abstractmethod
    async def find_by_blz(
        self,
        blz: str,
    ) -> Optional[StoredBankCredentials]:
        """
        Find encrypted credentials by bank code (current user).

        Returns the StoredBankCredentials entity with encrypted blobs.
        No decryption happens here!

        Parameters
        ----------
        blz
            Bankleitzahl (bank code)

        Returns
        -------
        StoredBankCredentials with encrypted fields, or None if not found
        """

    @abstractmethod
    async def find_by_id(
        self,
        credential_id: str,
    ) -> Optional[StoredBankCredentials]:
        """
        Find encrypted credentials by ID (must belong to current user).

        Parameters
        ----------
        credential_id
            Unique credential identifier

        Returns
        -------
        StoredBankCredentials with encrypted fields, or None if not found
        """

    @abstractmethod
    async def find_all(
        self,
    ) -> list[StoredBankCredentials]:
        """
        Find all encrypted credentials for the current user.

        Returns full entities (including encrypted fields) for admin/migration purposes.
        For user-facing lists, use BankCredentialRepository.find_all()
        which returns metadata only.

        Returns
        -------
        List of StoredBankCredentials entities
        """

    @abstractmethod
    async def delete(
        self,
        blz: str,
    ) -> bool:
        """
        Delete (soft delete) stored credentials for current user.

        Parameters
        ----------
        blz
            Bankleitzahl

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
        Update last_used_at timestamp for current user.

        Parameters
        ----------
        blz
            Bankleitzahl

        Raises
        ------
        CredentialNotFoundError
            If credentials not found
        """
