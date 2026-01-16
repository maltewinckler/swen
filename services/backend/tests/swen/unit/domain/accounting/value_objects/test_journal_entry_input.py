"""Unit tests for JournalEntryInput value object."""

from decimal import Decimal
from uuid import uuid4

import pytest

from swen.domain.accounting.value_objects import JournalEntryInput
from swen.domain.shared.exceptions import ValidationError


class TestJournalEntryInput:
    """Tests for the JournalEntryInput value object."""

    def test_create_debit_entry(self):
        """Create a valid debit entry."""
        account_id = uuid4()
        entry = JournalEntryInput.debit_entry(account_id, Decimal("100.00"))

        assert entry.account_id == account_id
        assert entry.debit == Decimal("100.00")
        assert entry.credit is None
        assert entry.is_debit is True
        assert entry.amount == Decimal("100.00")

    def test_create_credit_entry(self):
        """Create a valid credit entry."""
        account_id = uuid4()
        entry = JournalEntryInput.credit_entry(account_id, Decimal("50.50"))

        assert entry.account_id == account_id
        assert entry.debit is None
        assert entry.credit == Decimal("50.50")
        assert entry.is_debit is False
        assert entry.amount == Decimal("50.50")

    def test_create_direct_debit_entry(self):
        """Create debit entry directly with constructor."""
        account_id = uuid4()
        entry = JournalEntryInput(account_id=account_id, debit=Decimal("25.00"))

        assert entry.is_debit is True
        assert entry.amount == Decimal("25.00")

    def test_create_direct_credit_entry(self):
        """Create credit entry directly with constructor."""
        account_id = uuid4()
        entry = JournalEntryInput(account_id=account_id, credit=Decimal("75.00"))

        assert entry.is_debit is False
        assert entry.amount == Decimal("75.00")

    def test_reject_both_debit_and_credit(self):
        """Reject entry with both debit and credit."""
        account_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            JournalEntryInput(
                account_id=account_id,
                debit=Decimal("100.00"),
                credit=Decimal("50.00"),
            )

        assert "cannot have both" in str(exc_info.value).lower()

    def test_reject_zero_amounts(self):
        """Reject entry with zero amounts."""
        account_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            JournalEntryInput(
                account_id=account_id,
                debit=Decimal("0"),
                credit=Decimal("0"),
            )

        assert "greater than zero" in str(exc_info.value).lower()

    def test_reject_no_amounts(self):
        """Reject entry with no amounts."""
        account_id = uuid4()

        with pytest.raises(ValidationError):
            JournalEntryInput(account_id=account_id)

    def test_entry_is_immutable(self):
        """Entry is immutable (frozen dataclass)."""
        entry = JournalEntryInput.debit_entry(uuid4(), Decimal("100.00"))

        with pytest.raises(AttributeError):
            entry.debit = Decimal("200.00")  # type: ignore
