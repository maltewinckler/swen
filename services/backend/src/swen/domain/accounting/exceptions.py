"""Accounting domain exceptions."""

from typing import Any
from uuid import UUID

from swen.domain.shared.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    EntityNotFoundError,
    ErrorCode,
    ValidationError,
)


class AccountNotFoundError(EntityNotFoundError):
    """Raised when an accounting account cannot be found."""

    def __init__(
        self,
        account_id: str | UUID | None = None,
        account_number: str | None = None,
        account_name: str | None = None,
    ) -> None:
        identifier = account_id or account_number or account_name or "unknown"
        super().__init__(
            message=f"Account '{identifier}' not found",
            code=ErrorCode.ACCOUNT_NOT_FOUND,
            details={
                "account_id": str(account_id) if account_id else None,
                "account_number": account_number,
                "account_name": account_name,
            },
        )


class AccountAlreadyExistsError(ConflictError):
    """Raised when trying to create a duplicate account."""

    def __init__(
        self,
        account_name: str | None = None,
        account_number: str | None = None,
        message: str | None = None,
    ) -> None:
        if message:
            msg = message
            code = (
                ErrorCode.DUPLICATE_ACCOUNT_NUMBER
                if account_number
                else ErrorCode.DUPLICATE_ACCOUNT
            )
        elif account_number:
            msg = f"Account with number '{account_number}' already exists"
            code = ErrorCode.DUPLICATE_ACCOUNT_NUMBER
        elif account_name:
            msg = f"Account with name '{account_name}' already exists"
            code = ErrorCode.DUPLICATE_ACCOUNT
        else:
            msg = "Account already exists"
            code = ErrorCode.DUPLICATE_ACCOUNT

        super().__init__(
            message=msg,
            code=code,
            details={"account_name": account_name, "account_number": account_number},
        )


class AccountCannotBeDeactivatedError(BusinessRuleViolation):
    """Raised when trying to deactivate an account that cannot be deactivated."""

    def __init__(self, account_name: str) -> None:
        msg = f"Account '{account_name}' cannot be deactivated due to existing dependencies"  # NOQA: E501
        super().__init__(
            message=msg,
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details={"account_name": account_name},
        )


class DuplicateIbanMappingError(ConflictError):
    """Raised when an IBAN is already mapped to an account."""

    def __init__(self, iban: str) -> None:
        super().__init__(
            message=f"IBAN '{iban}' is already mapped to an account",
            code=ErrorCode.DUPLICATE_IBAN,
            details={"iban": iban},
        )


class InactiveAccountError(BusinessRuleViolation):
    """Raised when trying to use an inactive account."""

    def __init__(self, account_name: str) -> None:
        super().__init__(
            message=f"Account '{account_name}' is not active",
            code=ErrorCode.INACTIVE_ACCOUNT,
            details={"account_name": account_name},
        )


class InvalidAccountTypeError(ValidationError):
    """Raised when an invalid account type is provided."""

    def __init__(self, account_type: str, valid_types: list[str] | None = None) -> None:
        valid = (
            ", ".join(valid_types)
            if valid_types
            else "asset, liability, equity, income, expense"
        )
        super().__init__(
            message=f"Invalid account type '{account_type}'. Valid types: {valid}",
            code=ErrorCode.INVALID_ACCOUNT_TYPE,
            details={"account_type": account_type, "valid_types": valid_types},
        )


class TransactionNotFoundError(EntityNotFoundError):
    """Raised when a transaction cannot be found."""

    def __init__(self, transaction_id: str | UUID) -> None:
        super().__init__(
            message=f"Transaction '{transaction_id}' not found",
            code=ErrorCode.TRANSACTION_NOT_FOUND,
            details={"transaction_id": str(transaction_id)},
        )


class TransactionAlreadyPostedError(BusinessRuleViolation):
    """Raised when trying to modify a posted transaction."""

    def __init__(self, transaction_id: str | UUID | None = None) -> None:
        super().__init__(
            message="Cannot modify a posted transaction",
            code=ErrorCode.TRANSACTION_ALREADY_POSTED,
            details={"transaction_id": str(transaction_id)} if transaction_id else None,
        )


class TransactionAlreadyDraftError(BusinessRuleViolation):
    """Raised when trying to unpost a draft transaction."""

    def __init__(self, transaction_id: str | UUID | None = None) -> None:
        super().__init__(
            message="Transaction is already a draft",
            code=ErrorCode.TRANSACTION_ALREADY_DRAFT,
            details={"transaction_id": str(transaction_id)} if transaction_id else None,
        )


class UnbalancedTransactionError(BusinessRuleViolation):
    """Raised when transaction debits don't equal credits."""

    def __init__(self, debits: str, credits: str) -> None:
        super().__init__(
            message=f"Transaction not balanced: debits={debits}, credits={credits}",
            code=ErrorCode.UNBALANCED_TRANSACTION,
            details={"total_debits": debits, "total_credits": credits},
        )


class MixedCurrencyError(BusinessRuleViolation):
    """Raised when a transaction contains mixed currencies."""

    def __init__(self, currency1: str, currency2: str) -> None:
        super().__init__(
            message=f"Transaction has mixed currencies: {currency1} and {currency2}",
            code=ErrorCode.MIXED_CURRENCY,
            details={"currency1": currency1, "currency2": currency2},
        )


class UnsupportedCurrencyError(BusinessRuleViolation):
    """Raised when a non-supported currency is used."""

    def __init__(self, currency: str, supported: str = "EUR") -> None:
        super().__init__(
            message=f"Only {supported} is supported, got {currency}",
            code=ErrorCode.UNSUPPORTED_CURRENCY,
            details={"currency": currency, "supported": supported},
        )


class EmptyTransactionError(BusinessRuleViolation):
    """Raised when a transaction has fewer than 2 entries."""

    def __init__(self, entry_count: int = 0) -> None:
        super().__init__(
            message="Transaction must have at least 2 entries",
            code=ErrorCode.EMPTY_TRANSACTION,
            details={"entry_count": entry_count},
        )


class ZeroAmountError(ValidationError):
    """Raised when a zero amount is provided where non-zero is required."""

    def __init__(self, field: str = "amount") -> None:
        super().__init__(
            message=f"{field.capitalize()} must be non-zero",
            code=ErrorCode.ZERO_AMOUNT,
            details={"field": field},
        )


class InvalidTransactionMetadataError(ValidationError):
    """Raised when transaction metadata is invalid."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"Invalid transaction metadata: {reason}",
            code=ErrorCode.VALIDATION_ERROR,
            details={"reason": reason},
        )


class EmptyDescriptionError(ValidationError):
    """Raised when a transaction description is empty."""

    def __init__(self) -> None:
        super().__init__(
            message="Transaction description cannot be empty",
            code=ErrorCode.VALIDATION_ERROR,
        )


class ProtectedEntryError(BusinessRuleViolation):
    """Raised when attempting to modify a protected journal entry.

    Bank-imported transactions have protected asset entries that cannot
    be modified. This preserves reconciliation integrity with bank statements.
    To correct errors, create a reversal transaction instead.
    """

    def __init__(
        self,
        entry_id: UUID | None = None,
        reason: str = "bank import",
    ) -> None:
        super().__init__(
            message=(
                f"Cannot modify protected entry. "
                f"Entries from {reason} are immutable to preserve reconciliation. "
                f"Create a reversal transaction to correct errors."
            ),
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details={
                "entry_id": str(entry_id) if entry_id else None,
                "reason": reason,
            },
        )


class InvalidCurrencyError(ValidationError):
    """Raised when an invalid currency code is provided."""

    def __init__(
        self,
        currency: str,
        valid_currencies: list[str] | None = None,
    ) -> None:
        valid = ", ".join(valid_currencies) if valid_currencies else "EUR"
        super().__init__(
            message=f"Invalid currency '{currency}'. Valid currencies: {valid}",
            code=ErrorCode.INVALID_CURRENCY,
            details={"currency": currency, "valid_currencies": valid_currencies},
        )


class InvalidAmountError(ValidationError):
    """Raised when an invalid amount is provided."""

    def __init__(self, amount: Any, reason: str = "invalid format") -> None:
        super().__init__(
            message=f"Invalid amount '{amount}': {reason}",
            code=ErrorCode.INVALID_AMOUNT,
            details={"amount": str(amount), "reason": reason},
        )


class NegativeAmountError(ValidationError):
    """Raised when a negative amount is provided where positive is required."""

    def __init__(self, amount: Any) -> None:
        super().__init__(
            message=f"Amount must be positive, got {amount}",
            code=ErrorCode.INVALID_AMOUNT,
            details={"amount": str(amount)},
        )
