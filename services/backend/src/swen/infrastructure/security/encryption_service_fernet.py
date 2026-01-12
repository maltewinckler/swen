"""Fernet encryption service implementation."""

from cryptography.fernet import Fernet, InvalidToken

from swen.domain.security.exceptions import DecryptionError, EncryptionError
from swen.domain.security.services import EncryptionService


class FernetEncryptionService(EncryptionService):
    """Fernet-based encryption service implementation."""

    def __init__(self, encryption_key: bytes):
        try:
            self._fernet = Fernet(encryption_key)
        except (ValueError, TypeError) as e:
            msg = f"Invalid Fernet encryption key: {e}"
            raise ValueError(msg) from e

    def encrypt(self, plaintext: str) -> bytes:
        try:
            return self._fernet.encrypt(plaintext.encode("utf-8"))
        except Exception as e:
            msg = f"Encryption failed: {e}"
            raise EncryptionError(msg) from e

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as e:
            msg = "Decryption failed: Invalid token (wrong key or tampered data)"
            raise DecryptionError(msg) from e
        except Exception as e:
            msg = f"Decryption failed: {e}"
            raise DecryptionError(msg) from e

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()
