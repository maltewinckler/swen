"""Transaction source enum.

Defines the origin/source of accounting transactions.
This is a first-class domain concept used for filtering and business logic.
"""

from enum import Enum


class TransactionSource(str, Enum):
    """Origin of the transaction.

    Uses (str, Enum) for Python 3.10 compatibility (StrEnum is 3.11+).
    The string inheritance allows direct JSON serialization.
    """

    BANK_IMPORT = "bank_import"
    MANUAL = "manual"
    OPENING_BALANCE = "opening_balance"
    REVERSAL = "reversal"

    @classmethod
    def from_string(cls, value: str) -> "TransactionSource":
        try:
            return cls(value.lower())
        except ValueError:
            valid = [s.value for s in cls]
            msg = f"Unknown transaction source: {value}. Valid: {valid}"
            raise ValueError(msg) from None
