"""Transaction source enum.

Defines the origin/source of accounting transactions.
This is a first-class domain concept used for filtering and business logic.
"""

from enum import Enum


class TransactionSource(str, Enum):
    """Origin of the transaction."""

    BANK_IMPORT = "bank_import"
    MANUAL = "manual"
    OPENING_BALANCE = "opening_balance"
    OPENING_BALANCE_ADJUSTMENT = "opening_balance_adjustment"
    REVERSAL = "reversal"

    @classmethod
    def from_string(cls, value: str) -> "TransactionSource":
        try:
            return cls(value.lower())
        except ValueError:
            valid = [s.value for s in cls]
            msg = f"Unknown transaction source: {value}. Valid: {valid}"
            raise ValueError(msg) from None
