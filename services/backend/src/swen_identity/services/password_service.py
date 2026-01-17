"""Password hashing service using bcrypt.

Provides secure password hashing and verification with configurable
strength validation.
"""

import bcrypt

from swen_identity.exceptions import WeakPasswordError


class PasswordHashingService:
    """Service for secure password hashing and verification.

    Uses bcrypt for password hashing with configurable work factor.
    Also provides password strength validation.

    Examples
    --------
    >>> service = PasswordHashingService()
    >>> hash = service.hash("my_secure_password")
    >>> service.verify("my_secure_password", hash)
    True
    >>> service.verify("wrong_password", hash)
    False
    """

    # Password requirements
    MIN_LENGTH = 8
    MAX_LENGTH = 128

    def __init__(self, rounds: int = 12):
        """Initialize the password hashing service.

        Parameters
        ----------
        rounds
            The bcrypt work factor (log2 of iterations). Default is 12,
            which is a good balance of security and performance.
            Higher values are more secure but slower.
        """
        self._rounds = rounds

    def hash(self, password: str) -> str:
        """Hash a plaintext password.

        Parameters
        ----------
        password
            The plaintext password to hash

        Returns
        -------
        The bcrypt hash as a string

        Raises
        ------
        WeakPasswordError
            If password doesn't meet requirements
        """
        self.validate_strength(password)
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash.

        Parameters
        ----------
        password
            The plaintext password to check
        password_hash
            The bcrypt hash to verify against

        Returns
        -------
        True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            # Invalid hash format
            return False

    def validate_strength(self, password: str) -> None:
        """Validate that a password meets strength requirements.

        Current requirements:
        - Minimum 8 characters
        - Maximum 128 characters

        Parameters
        ----------
        password
            The password to validate

        Raises
        ------
        WeakPasswordError
            If password doesn't meet requirements
        """
        if not password:
            msg = "Password cannot be empty"
            raise WeakPasswordError(msg)

        if len(password) < self.MIN_LENGTH:
            msg = f"Password must be at least {self.MIN_LENGTH} characters"
            raise WeakPasswordError(
                msg,
            )

        if len(password) > self.MAX_LENGTH:
            msg = f"Password cannot exceed {self.MAX_LENGTH} characters"
            raise WeakPasswordError(
                msg,
            )

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if a password hash needs to be rehashed.

        This is useful when upgrading the work factor. After changing
        the rounds setting, existing hashes can be identified for
        rehashing on next login.

        Parameters
        ----------
        password_hash
            The existing hash to check

        Returns
        -------
        True if the hash should be regenerated
        """
        try:
            # Extract rounds from hash (bcrypt format: $2b$XX$...)
            parts = password_hash.split("$")
            if len(parts) >= 3:
                current_rounds = int(parts[2])
                return current_rounds != self._rounds
        except (ValueError, IndexError):
            pass
        return True
