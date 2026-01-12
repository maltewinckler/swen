"""Shared domain exceptions and error codes.

This module defines the base exception hierarchy and error codes for the
entire domain layer. All domain exceptions should inherit from DomainException
to enable centralized exception handling in the presentation layer.
"""

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Stable error codes for API clients.

    These codes are part of the public API contract. Should not be changed.
    """

    # Validation Errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_IBAN = "INVALID_IBAN"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INVALID_DATE = "INVALID_DATE"
    INVALID_CURRENCY = "INVALID_CURRENCY"
    INVALID_ACCOUNT_TYPE = "INVALID_ACCOUNT_TYPE"

    # Not Found Errors (404)
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    CREDENTIALS_NOT_FOUND = "CREDENTIALS_NOT_FOUND"
    MAPPING_NOT_FOUND = "MAPPING_NOT_FOUND"
    BANK_NOT_FOUND = "BANK_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Conflict Errors (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_ACCOUNT = "DUPLICATE_ACCOUNT"
    DUPLICATE_ACCOUNT_NUMBER = "DUPLICATE_ACCOUNT_NUMBER"
    DUPLICATE_IBAN = "DUPLICATE_IBAN"
    CREDENTIALS_ALREADY_EXIST = "CREDENTIALS_ALREADY_EXIST"

    # Business Rule Violations (422)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    TRANSACTION_ALREADY_POSTED = "TRANSACTION_ALREADY_POSTED"
    TRANSACTION_ALREADY_DRAFT = "TRANSACTION_ALREADY_DRAFT"
    UNBALANCED_TRANSACTION = "UNBALANCED_TRANSACTION"
    MIXED_CURRENCY = "MIXED_CURRENCY"
    UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT"
    EMPTY_TRANSACTION = "EMPTY_TRANSACTION"
    ZERO_AMOUNT = "ZERO_AMOUNT"

    # Banking Errors (503/504)
    BANK_CONNECTION_FAILED = "BANK_CONNECTION_FAILED"
    BANK_AUTHENTICATION_FAILED = "BANK_AUTHENTICATION_FAILED"
    BANK_TRANSACTION_FETCH_FAILED = "BANK_TRANSACTION_FETCH_FAILED"
    TAN_TIMEOUT = "TAN_TIMEOUT"
    TAN_CANCELLED = "TAN_CANCELLED"

    # Sync/Integration Errors
    SYNC_FAILED = "SYNC_FAILED"
    NO_CREDENTIALS = "NO_CREDENTIALS"
    NO_ACCOUNT_MAPPINGS = "NO_ACCOUNT_MAPPINGS"
    IMPORT_FAILED = "IMPORT_FAILED"

    # Security Errors
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    DECRYPTION_FAILED = "DECRYPTION_FAILED"
    INVALID_ENCRYPTION_KEY = "INVALID_ENCRYPTION_KEY"

    # Concurrency Errors
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"

    # General Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DomainException(Exception):  # NOQA: N818
    """Base exception for all domain-related errors.

    This exception provides structured error information that can be
    used by the presentation layer to generate consistent API responses.

    Attributes
    ----------
    message
        Human-readable error message (safe for end users)
    code
        Stable error code for programmatic handling
    details
        Optional additional context (logged but not exposed to users)
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code.value!r}, "
            f"details={self.details!r})"
        )


class ValidationError(DomainException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


class BusinessRuleViolation(DomainException):
    """Raised when a business rule or domain invariant is violated."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.BUSINESS_RULE_VIOLATION,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


class EntityNotFoundError(DomainException):
    """Raised when a requested entity cannot be found."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.ENTITY_NOT_FOUND,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


class ConflictError(DomainException):
    """Raised when an operation conflicts with existing state."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONFLICT,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


class ConcurrencyError(DomainException):
    """Raised when concurrent modifications conflict."""

    def __init__(
        self,
        message: str = "The resource was modified by another request",
        code: ErrorCode = ErrorCode.CONCURRENCY_CONFLICT,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)
