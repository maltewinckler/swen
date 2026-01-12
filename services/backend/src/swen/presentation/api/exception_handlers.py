"""Centralized exception handlers for the FastAPI application.

This module provides a unified approach to exception handling across all
API endpoints. Domain exceptions are automatically mapped to appropriate
HTTP responses with consistent error format.

Error Response Format:
    {
        "detail": "Human-readable error message",
        "code": "MACHINE_READABLE_ERROR_CODE"
    }

Usage:
    from swen.presentation.api.exception_handlers import setup_exception_handlers

    app = FastAPI()
    setup_exception_handlers(app)
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from swen.domain.banking.exceptions import (
    BankAuthenticationError,
    BankConnectionError,
    BankingDomainError,
    TanTimeoutError,
)
from swen.domain.shared.exceptions import (
    BusinessRuleViolation,
    ConcurrencyError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    ErrorCode,
    ValidationError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Error Code to HTTP Status Mapping
# =============================================================================

ERROR_CODE_TO_STATUS: dict[ErrorCode, int] = {
    # 400 Bad Request - validation errors
    ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_FORMAT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_IBAN: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_AMOUNT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_DATE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_CURRENCY: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_ACCOUNT_TYPE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNBALANCED_TRANSACTION: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ZERO_AMOUNT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.NO_CREDENTIALS: status.HTTP_400_BAD_REQUEST,
    ErrorCode.NO_ACCOUNT_MAPPINGS: status.HTTP_400_BAD_REQUEST,
    # 404 Not Found
    ErrorCode.ENTITY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.ACCOUNT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.TRANSACTION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CREDENTIALS_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.MAPPING_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.BANK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.USER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    # 409 Conflict - already exists
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.DUPLICATE_ACCOUNT: status.HTTP_409_CONFLICT,
    ErrorCode.DUPLICATE_ACCOUNT_NUMBER: status.HTTP_409_CONFLICT,
    ErrorCode.DUPLICATE_IBAN: status.HTTP_409_CONFLICT,
    ErrorCode.CREDENTIALS_ALREADY_EXIST: status.HTTP_409_CONFLICT,
    ErrorCode.CONCURRENCY_CONFLICT: status.HTTP_409_CONFLICT,
    # 422 Unprocessable Entity - business rule violations
    ErrorCode.BUSINESS_RULE_VIOLATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.TRANSACTION_ALREADY_POSTED: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.TRANSACTION_ALREADY_DRAFT: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.MIXED_CURRENCY: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.UNSUPPORTED_CURRENCY: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.INACTIVE_ACCOUNT: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.EMPTY_TRANSACTION: status.HTTP_422_UNPROCESSABLE_ENTITY,
    # 401 Unauthorized - authentication errors
    ErrorCode.BANK_AUTHENTICATION_FAILED: status.HTTP_401_UNAUTHORIZED,
    # 503 Service Unavailable - external service errors
    ErrorCode.BANK_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.BANK_TRANSACTION_FETCH_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.SYNC_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.IMPORT_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    # 504 Gateway Timeout
    ErrorCode.TAN_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
    ErrorCode.TAN_CANCELLED: status.HTTP_400_BAD_REQUEST,
    # Security errors
    ErrorCode.ENCRYPTION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.DECRYPTION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.INVALID_ENCRYPTION_KEY: status.HTTP_500_INTERNAL_SERVER_ERROR,
    # 500 Internal Server Error
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _get_status_for_exception(exc: DomainException) -> int:  # NOQA: PLR0911
    """Determine HTTP status code for a domain exception.

    Uses the error code mapping, with fallback based on exception type.
    """
    # First try error code mapping
    if exc.code in ERROR_CODE_TO_STATUS:
        return ERROR_CODE_TO_STATUS[exc.code]

    # Fallback based on exception type hierarchy
    if isinstance(exc, EntityNotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, ConflictError):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, ValidationError):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(exc, BusinessRuleViolation):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(exc, ConcurrencyError):
        return status.HTTP_409_CONFLICT

    # Default to 400 for domain exceptions
    return status.HTTP_400_BAD_REQUEST


def _create_error_response(
    status_code: int,
    message: str,
    code: str,
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "code": code,
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application.

    This should be called during app initialization to enable centralized
    exception handling for all domain exceptions.

    Parameters
    ----------
    app
        The FastAPI application instance
    """

    @app.exception_handler(DomainException)
    async def domain_exception_handler(
        request: Request,
        exc: DomainException,
    ) -> JSONResponse:
        """Handle all domain exceptions with structured response.

        Logs the full exception details for debugging while returning
        a safe, user-friendly message to the client.
        """
        status_code = _get_status_for_exception(exc)

        # Log with details for debugging (includes request info)
        logger.warning(
            "Domain exception on %s %s: %s (code=%s, details=%s)",
            request.method,
            request.url.path,
            exc.message,
            exc.code.value,
            exc.details,
        )

        return _create_error_response(
            status_code=status_code,
            message=exc.message,
            code=exc.code.value,
        )

    @app.exception_handler(BankingDomainError)
    async def banking_exception_handler(
        request: Request,
        exc: BankingDomainError,
    ) -> JSONResponse:
        """Handle banking domain exceptions.

        Banking errors are logged at warning level since they often
        indicate external service issues rather than application bugs.
        """
        # Specific handling for authentication errors
        if isinstance(exc, BankAuthenticationError):
            logger.warning(
                "Bank authentication failed on %s %s: %s",
                request.method,
                request.url.path,
                exc.message,
            )
            return _create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Bank authentication failed. Please check your credentials.",
                code=ErrorCode.BANK_AUTHENTICATION_FAILED.value,
            )

        # Specific handling for TAN timeout
        if isinstance(exc, TanTimeoutError):
            logger.warning(
                "TAN timeout on %s %s: %s",
                request.method,
                request.url.path,
                exc.message,
            )
            return _create_error_response(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                message=exc.message,
                code=ErrorCode.TAN_TIMEOUT.value,
            )

        # General bank connection errors
        if isinstance(exc, BankConnectionError):
            logger.warning(
                "Bank connection error on %s %s: %s",
                request.method,
                request.url.path,
                exc.message,
            )
            return _create_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to connect to bank. Please try again later.",
                code=ErrorCode.BANK_CONNECTION_FAILED.value,
            )

        # Other banking errors
        status_code = _get_status_for_exception(exc)
        logger.warning(
            "Banking error on %s %s: %s (code=%s)",
            request.method,
            request.url.path,
            exc.message,
            exc.code.value,
        )

        return _create_error_response(
            status_code=status_code,
            message=exc.message,
            code=exc.code.value,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unhandled exceptions with consistent error format.

        This is the catch-all handler for any exceptions not handled by
        the domain-specific handlers above. It ensures clients always
        receive a consistent error response format.
        """
        logger.exception(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )
        return _create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An internal error occurred",
            code=ErrorCode.INTERNAL_ERROR.value,
        )
