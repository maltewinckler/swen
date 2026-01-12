"""Integration domain exceptions.

This module defines exceptions specific to the integration bounded context,
which bridges the banking and accounting domains. This includes sync errors,
import failures, and account mapping issues.

These exceptions inherit from the shared DomainException base class and
provide semantic error information that maps to appropriate HTTP responses.
"""

from uuid import UUID

from swen.domain.shared.exceptions import (
    DomainException,
    EntityNotFoundError,
    ErrorCode,
    ValidationError,
)


class IntegrationError(DomainException):
    """Base exception for integration domain errors."""


class MappingNotFoundError(EntityNotFoundError):
    """Raised when an account mapping cannot be found."""

    def __init__(self, iban: str) -> None:
        super().__init__(
            message=f"No account mapping found for IBAN: {iban}",
            code=ErrorCode.MAPPING_NOT_FOUND,
            details={"iban": iban},
        )


class MappingAccountNotFoundError(EntityNotFoundError):
    """Raised when the linked accounting account for a mapping is not found."""

    def __init__(self, mapping_id: str | UUID, account_id: str | UUID) -> None:
        super().__init__(
            message="Account mapping exists but linked accounting account not found",
            code=ErrorCode.ACCOUNT_NOT_FOUND,
            details={
                "mapping_id": str(mapping_id),
                "accounting_account_id": str(account_id),
            },
        )


class SyncError(IntegrationError):
    """Base exception for sync-related errors."""


class NoCredentialsError(SyncError):
    """Raised when credentials are required but not found."""

    def __init__(self, blz: str | None = None) -> None:
        if blz:
            msg = f"No stored credentials found for BLZ {blz}. Store credentials first."
        else:
            msg = "No bank credentials found. Please set up bank credentials first."
        super().__init__(
            message=msg,
            code=ErrorCode.NO_CREDENTIALS,
            details={"blz": blz} if blz else None,
        )


class NoAccountMappingsError(SyncError):
    """Raised when sync is attempted without any account mappings."""

    def __init__(self) -> None:
        super().__init__(
            message="No bank accounts are set up. Please connect a bank first.",
            code=ErrorCode.NO_ACCOUNT_MAPPINGS,
        )


class SyncFailedError(SyncError):
    """Raised when a sync operation fails."""

    def __init__(self, reason: str, iban: str | None = None) -> None:
        super().__init__(
            message=f"Sync failed: {reason}",
            code=ErrorCode.SYNC_FAILED,
            details={"reason": reason, "iban": iban} if iban else {"reason": reason},
        )


class DataImportError(IntegrationError):
    """Base exception for import-related errors."""


class ImportFailedError(DataImportError):
    """Raised when transaction import fails."""

    def __init__(self, reason: str, transaction_ref: str | None = None) -> None:
        super().__init__(
            message=f"Import failed: {reason}",
            code=ErrorCode.IMPORT_FAILED,
            details={"reason": reason, "transaction_ref": transaction_ref},
        )


class DuplicateImportError(DataImportError):
    """Raised when attempting to import a duplicate transaction."""

    def __init__(self, transaction_hash: str | None = None) -> None:
        super().__init__(
            message="Transaction has already been imported",
            code=ErrorCode.CONFLICT,
            details={"transaction_hash": transaction_hash}
            if transaction_hash
            else None,
        )


class InvalidIbanError(ValidationError):
    """Raised when an IBAN is invalid."""

    def __init__(self, iban: str, reason: str = "invalid format") -> None:
        super().__init__(
            message=f"Invalid IBAN '{iban}': {reason}",
            code=ErrorCode.INVALID_IBAN,
            details={"iban": iban, "reason": reason},
        )


class EmptyIbanError(ValidationError):
    """Raised when an IBAN is empty."""

    def __init__(self) -> None:
        super().__init__(
            message="IBAN cannot be empty",
            code=ErrorCode.INVALID_IBAN,
        )


class IbanExtractionError(ValidationError):
    """Raised when BLZ cannot be extracted from an IBAN."""

    def __init__(self, iban: str) -> None:
        super().__init__(
            message=f"Cannot extract BLZ from IBAN {iban}",
            code=ErrorCode.INVALID_IBAN,
            details={"iban": iban},
        )
