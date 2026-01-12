"""Transaction import entity for tracking import history."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid5

from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.time import utc_now

# This is different from account mapping namespace
TRANSACTION_IMPORT_NAMESPACE = UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e")


class TransactionImport:
    """
    Tracks the import history of bank transactions into accounting system.

    Purpose:
    - Ensures idempotency (don't import same transaction twice)
    - Provides audit trail (bank transaction -> accounting transaction)
    - Allows re-import of failed transactions
    - Enables import analytics and troubleshooting

    Deduplication Strategy:
    - Uses bank_transaction_id (FK to bank_transactions table)
    - Each stored bank transaction has a unique ID via hash + sequence
    """

    def __init__(  # noqa: PLR0913
        self,
        user_id: UUID,
        bank_transaction_id: UUID,
        status: ImportStatus = ImportStatus.PENDING,
        accounting_transaction_id: Optional[UUID] = None,
        error_message: Optional[str] = None,
        # For reconstitution from persistence:
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        imported_at: Optional[datetime] = None,
    ):
        self._user_id = user_id
        self._bank_transaction_id = bank_transaction_id

        # Use provided ID or generate deterministic UUID
        if id is not None:
            self._id = id
        else:
            name = f"{user_id}:{bank_transaction_id}"
            self._id = uuid5(TRANSACTION_IMPORT_NAMESPACE, name)

        self._status = status
        self._accounting_transaction_id = accounting_transaction_id
        self._error_message = error_message
        self._created_at = created_at or utc_now()
        self._updated_at = updated_at or utc_now()
        self._imported_at = imported_at

        self._validate()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def bank_transaction_id(self) -> UUID:
        return self._bank_transaction_id

    @property
    def status(self) -> ImportStatus:
        return self._status

    @property
    def accounting_transaction_id(self) -> Optional[UUID]:
        return self._accounting_transaction_id

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def imported_at(self) -> Optional[datetime]:
        return self._imported_at

    def _validate(self) -> None:
        # If status is SUCCESS, must have accounting_transaction_id
        if self._status == ImportStatus.SUCCESS and not self._accounting_transaction_id:
            msg = "Successful import must have accounting transaction ID"
            raise ValueError(msg)

        # If status is FAILED, must have error_message
        if self._status == ImportStatus.FAILED and not self._error_message:
            msg = "Failed import must have error message"
            raise ValueError(msg)

    def mark_as_imported(self, accounting_transaction_id: UUID) -> None:
        if self._status == ImportStatus.SUCCESS:
            msg = "Transaction already imported successfully"
            raise ValueError(msg)

        self._status = ImportStatus.SUCCESS
        self._accounting_transaction_id = accounting_transaction_id
        self._error_message = None  # Clear any previous error
        self._imported_at = utc_now()
        self._updated_at = utc_now()

    def mark_as_failed(self, error_message: str) -> None:
        if not error_message or not error_message.strip():
            msg = "Error message cannot be empty"
            raise ValueError(msg)

        self._status = ImportStatus.FAILED
        self._error_message = error_message.strip()
        self._updated_at = utc_now()

    def mark_as_duplicate(self) -> None:
        self._status = ImportStatus.DUPLICATE
        self._updated_at = utc_now()

    def mark_as_skipped(self, reason: str) -> None:
        self._status = ImportStatus.SKIPPED
        self._error_message = reason
        self._updated_at = utc_now()

    def retry(self) -> None:
        if self._status == ImportStatus.SUCCESS:
            msg = "Cannot retry successful import"
            raise ValueError(msg)

        self._status = ImportStatus.PENDING
        self._error_message = None
        self._updated_at = utc_now()

    def is_imported(self) -> bool:
        return self._status == ImportStatus.SUCCESS

    def is_failed(self) -> bool:
        return self._status == ImportStatus.FAILED

    def is_duplicate(self) -> bool:
        return self._status == ImportStatus.DUPLICATE

    def is_skipped(self) -> bool:
        return self._status == ImportStatus.SKIPPED

    def can_retry(self) -> bool:
        return self._status in [ImportStatus.FAILED, ImportStatus.SKIPPED]

    @classmethod
    def reconstitute(  # noqa: PLR0913
        cls,
        id: UUID,
        user_id: UUID,
        bank_transaction_id: UUID,
        status: ImportStatus,
        accounting_transaction_id: Optional[UUID],
        error_message: Optional[str],
        created_at: datetime,
        updated_at: datetime,
        imported_at: Optional[datetime],
    ) -> "TransactionImport":
        return cls(
            user_id=user_id,
            bank_transaction_id=bank_transaction_id,
            status=status,
            accounting_transaction_id=accounting_transaction_id,
            error_message=error_message,
            id=id,
            created_at=created_at,
            updated_at=updated_at,
            imported_at=imported_at,
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, TransactionImport):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        return f"TransactionImport[{self._status.value}]: {self._bank_transaction_id}"
