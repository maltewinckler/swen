"""Security domain exceptions."""


class SecurityDomainError(Exception):
    """Base exception for security domain."""


class EncryptionError(SecurityDomainError):
    """Raised when encryption fails."""


class DecryptionError(SecurityDomainError):
    """Raised when decryption fails."""


class CredentialNotFoundError(SecurityDomainError):
    """Raised when stored credentials are not found."""


class InvalidEncryptionKeyError(SecurityDomainError):
    """Raised when encryption key is invalid or missing."""
