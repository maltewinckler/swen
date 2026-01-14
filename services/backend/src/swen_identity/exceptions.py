"""Identity and authentication exceptions.

These exceptions are raised by the swen_identity package and should be
caught and handled by the application layer.
"""


class AuthError(Exception):
    """Base exception for all authentication errors."""

    def __init__(self, message: str = "Authentication error"):
        self.message = message
        super().__init__(self.message)


class InvalidTokenError(AuthError):
    """Raised when a JWT token is invalid, expired, or malformed."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class WeakPasswordError(AuthError):
    """Raised when a password doesn't meet strength requirements."""

    def __init__(self, message: str = "Password does not meet requirements"):
        super().__init__(message)


class InvalidCredentialsError(AuthError):
    """Raised when email or password is incorrect during login."""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)


class AccountLockedError(AuthError):
    """Raised when an account is locked due to too many failed login attempts."""

    def __init__(
        self,
        message: str = "Account is locked due to too many failed login attempts",
        locked_until: str | None = None,
    ):
        self.locked_until = locked_until
        if locked_until:
            message = f"{message}. Try again after {locked_until}"
        super().__init__(message)


class InvalidRefreshTokenError(AuthError):
    """Raised when a refresh token is invalid."""

    def __init__(self, message: str = "Invalid refresh token"):
        super().__init__(message)


class RefreshTokenExpiredError(AuthError):
    """Raised when a refresh token has expired."""

    def __init__(self, message: str = "Refresh token has expired"):
        super().__init__(message)


class InvalidResetTokenError(AuthError):
    """Raised when a password reset token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired password reset token"):
        super().__init__(message)


class PasswordResetRateLimitError(AuthError):
    """Raised when a password reset request is rate limited."""

    def __init__(
        self,
        message: str = "Too many password reset requests. Try again later.",
    ):
        super().__init__(message)
