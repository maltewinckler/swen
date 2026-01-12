"""Journal entry entity for representing double-entry transactions."""

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from swen.domain.accounting.entities.account import Account
from swen.domain.accounting.value_objects import Money


class JournalEntry:
    """One side of a double-entry transaction."""

    def __init__(
        self,
        account: Account,
        debit: Optional[Money] = None,
        credit: Optional[Money] = None,
    ):
        # Validate that exactly one of debit or credit is provided
        if (debit is None) == (credit is None):
            msg = "Entry must have exactly one of debit or credit, not both or neither"
            raise ValueError(msg)

        # Validate amounts are positive
        if debit is not None and debit.is_negative():
            msg = "Debit amount must be positive"
            raise ValueError(msg)

        if credit is not None and credit.is_negative():
            msg = "Credit amount must be positive"
            raise ValueError(msg)

        self._id = uuid4()
        self._account = account
        self._debit = debit or Money(Decimal(0))
        self._credit = credit or Money(Decimal(0))

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def account(self) -> Account:
        return self._account

    @property
    def debit(self) -> Money:
        return self._debit

    @property
    def credit(self) -> Money:
        return self._credit

    @property
    def amount(self) -> Money:
        return self._debit if self._debit.is_positive() else self._credit

    def is_debit(self) -> bool:
        return self._debit.is_positive()

    def is_credit(self) -> bool:
        return self._credit.is_positive()

    def __eq__(self, other) -> bool:
        if not isinstance(other, JournalEntry):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Make hashable for use in sets and dicts."""
        return hash(self._id)

    def __str__(self) -> str:
        if self.is_debit():
            return f"Debit {self._account.name}: {self._debit}"
        return f"Credit {self._account.name}: {self._credit}"
