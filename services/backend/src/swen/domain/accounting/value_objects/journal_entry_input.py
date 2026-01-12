"""Value object for journal entry input in transaction creation.

This value object represents the input for creating a journal entry,
ensuring exactly one of debit or credit is specified with a positive amount.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from swen.domain.shared.exceptions import ValidationError


@dataclass(frozen=True)
class JournalEntryInput:
    """
    Immutable input specification for a single journal entry.

    In double-entry bookkeeping, each entry is either a debit OR a credit,
    never both. This value object enforces that constraint at construction time.
    """

    account_id: UUID
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None

    def __post_init__(self) -> None:
        """Validate that exactly one of debit or credit is set with positive amount."""
        has_debit = self.debit is not None and self.debit > 0
        has_credit = self.credit is not None and self.credit > 0

        if has_debit and has_credit:
            msg = "Journal entry cannot have both debit and credit amounts"
            raise ValidationError(msg)

        if not has_debit and not has_credit:
            msg = "Journal entry must have a debit or credit amount greater than zero"
            raise ValidationError(msg)

    @property
    def is_debit(self) -> bool:
        """Check if this is a debit entry."""
        return self.debit is not None and self.debit > 0

    @property
    def amount(self) -> Decimal:
        """Get the entry amount (whichever is set)."""
        if self.is_debit:
            return self.debit  # type: ignore  NOQA: PGH003
        return self.credit  # type: ignore  NOQA: PGH003

    @classmethod
    def debit_entry(cls, account_id: UUID, amount: Decimal) -> "JournalEntryInput":
        """Factory method to create a debit entry."""
        return cls(account_id=account_id, debit=amount)

    @classmethod
    def credit_entry(cls, account_id: UUID, amount: Decimal) -> "JournalEntryInput":
        """Factory method to create a credit entry."""
        return cls(account_id=account_id, credit=amount)
