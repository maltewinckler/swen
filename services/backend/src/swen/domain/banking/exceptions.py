"""Banking domain exceptions.

This module defines exceptions specific to the banking bounded context,
including bank connection errors, authentication failures, and TAN-related
issues.

These exceptions represent errors from external bank integrations and
typically map to 5xx HTTP responses (service unavailable, gateway timeout).
"""

from swen.domain.shared.exceptions import (
    DomainException,
    EntityNotFoundError,
    ErrorCode,
)

# =============================================================================
# Base Banking Exception
# =============================================================================


class BankingDomainError(DomainException):
    """Base exception for banking domain errors.

    All banking-related exceptions should inherit from this class to
    enable consistent handling of bank integration issues.
    """


# =============================================================================
# Connection Exceptions
# =============================================================================


class BankConnectionError(BankingDomainError):
    """Raised when bank connection fails.

    This is a general connection error. Use more specific subclasses
    when the cause is known (e.g., BankAuthenticationError).
    """

    def __init__(
        self,
        message: str = "Failed to connect to bank",
        blz: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.BANK_CONNECTION_FAILED,
            details={"blz": blz} if blz else None,
        )


class BankAuthenticationError(BankConnectionError):
    """Raised when bank authentication fails.

    This typically means invalid username/PIN or the bank rejected
    the login attempt.
    """

    def __init__(
        self,
        message: str = "Bank authentication failed. Please check your credentials.",
        blz: str | None = None,
    ) -> None:
        super().__init__(message=message, blz=blz)
        self.code = ErrorCode.BANK_AUTHENTICATION_FAILED


# =============================================================================
# TAN Exceptions
# =============================================================================


class TanError(BankingDomainError):
    """Base exception for TAN-related errors."""


class TanTimeoutError(TanError):
    """Raised when TAN approval times out.

    This occurs when the user doesn't approve the TAN request within
    the allowed time window (typically 5 minutes for decoupled TAN).
    """

    def __init__(
        self,
        message: str = "TAN approval timed out. Please try again.",
        timeout_seconds: int | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.TAN_TIMEOUT,
            details={"timeout_seconds": timeout_seconds} if timeout_seconds else None,
        )


class TanCancelledError(TanError):
    """Raised when TAN approval is cancelled by the user."""

    def __init__(
        self,
        message: str = "TAN approval was cancelled.",
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.TAN_CANCELLED,
        )


class TanRequiredError(TanError):
    """Raised when an operation requires TAN but no TAN callback is available."""

    def __init__(
        self,
        message: str = "This operation requires TAN approval. Please use interactive mode.",  # NOQA: E501
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
        )


# =============================================================================
# Account Exceptions
# =============================================================================


class BankAccountNotFoundError(EntityNotFoundError):
    """Raised when a bank account is not found.

    This is different from AccountNotFoundError (accounting domain) -
    this refers to accounts at the bank, not in our bookkeeping system.
    """

    def __init__(
        self,
        iban: str | None = None,
        message: str | None = None,
    ) -> None:
        msg = (
            message or f"Bank account '{iban}' not found"
            if iban
            else "Bank account not found"
        )
        super().__init__(
            message=msg,
            code=ErrorCode.ACCOUNT_NOT_FOUND,
            details={"iban": iban} if iban else None,
        )


# =============================================================================
# Transaction Fetch Exceptions
# =============================================================================


class BankTransactionFetchError(BankingDomainError):
    """Raised when fetching transactions from the bank fails."""

    def __init__(
        self,
        message: str = "Failed to fetch transactions from bank",
        iban: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.BANK_TRANSACTION_FETCH_FAILED,
            details={"iban": iban, "reason": reason},
        )


# =============================================================================
# Credentials Exceptions
# =============================================================================


class CredentialsNotFoundError(EntityNotFoundError):
    """Raised when stored credentials are not found."""

    def __init__(self, blz: str | None = None) -> None:
        msg = f"No credentials found for BLZ {blz}" if blz else "No credentials found"
        super().__init__(
            message=msg,
            code=ErrorCode.CREDENTIALS_NOT_FOUND,
            details={"blz": blz} if blz else None,
        )


class CredentialsAlreadyExistError(DomainException):
    """Raised when credentials already exist for a bank."""

    def __init__(self, blz: str) -> None:
        super().__init__(
            message=f"Credentials already exist for BLZ {blz}",
            code=ErrorCode.CREDENTIALS_ALREADY_EXIST,
            details={"blz": blz},
        )


class InvalidCredentialsFormatError(DomainException):
    """Raised when credential format is invalid."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"Invalid credentials: {reason}",
            code=ErrorCode.VALIDATION_ERROR,
            details={"reason": reason},
        )


# =============================================================================
# Bank Lookup Exceptions
# =============================================================================


class BankNotFoundError(EntityNotFoundError):
    """Raised when a bank is not found in the institute directory."""

    def __init__(self, blz: str) -> None:
        super().__init__(
            message=f"Bank with BLZ {blz} not found in institute directory",
            code=ErrorCode.BANK_NOT_FOUND,
            details={"blz": blz},
        )


class InvalidBlzFormatError(DomainException):
    """Raised when BLZ format is invalid."""

    def __init__(self, blz: str) -> None:
        super().__init__(
            message="BLZ must be exactly 8 digits",
            code=ErrorCode.INVALID_FORMAT,
            details={"blz": blz},
        )
