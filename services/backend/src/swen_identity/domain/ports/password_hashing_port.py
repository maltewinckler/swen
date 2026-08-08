"""Port for password hashing, verification, and strength validation.

Deliberately technology-agnostic: the current implementation is bcrypt,
but nothing in the application layer should need to know that.
"""

from abc import ABC, abstractmethod


class PasswordHashingPort(ABC):
    """Port for secure password hashing and verification."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plaintext password, raising if it fails strength requirements."""

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against a hash."""

    @abstractmethod
    def validate_strength(self, password: str) -> None:
        """Validate that a password meets strength requirements, raising if not."""

    @abstractmethod
    def needs_rehash(self, password_hash: str) -> bool:
        """Check whether an existing hash should be regenerated."""
