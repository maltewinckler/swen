"""Encryption service interface for the Security domain."""

from abc import ABC, abstractmethod


class EncryptionService(ABC):
    """Domain service interface for encryption operations."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt plaintext string to bytes.

        Parameters
        ----------
        plaintext
            The sensitive data to encrypt

        Returns
        -------
        Encrypted bytes (ciphertext)

        Raises
        ------
        EncryptionError
            If encryption fails
        """

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt bytes back to plaintext string.

        Parameters
        ----------
        ciphertext
            The encrypted data

        Returns
        -------
        Decrypted plaintext string

        Raises
        ------
        DecryptionError
            If decryption fails (wrong key, tampered data)
        """
