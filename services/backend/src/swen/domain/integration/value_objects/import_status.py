"""Import status enumeration."""

from enum import Enum


class ImportStatus(Enum):
    """Status of a transaction import operation."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"

    def is_final(self) -> bool:
        return self in [
            ImportStatus.SUCCESS,
            ImportStatus.DUPLICATE,
        ]

    def is_error(self) -> bool:
        return self in [
            ImportStatus.FAILED,
        ]

    def can_retry(self) -> bool:
        return self in [ImportStatus.FAILED, ImportStatus.SKIPPED]
