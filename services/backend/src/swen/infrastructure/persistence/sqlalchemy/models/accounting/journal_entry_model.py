"""SQLAlchemy model for journal entries."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from swen.infrastructure.persistence.sqlalchemy.models.base import (
    Base,
    TimestampMixin,
)

if TYPE_CHECKING:
    from swen.infrastructure.persistence.sqlalchemy.models.accounting.account_model import (  # NOQA: E501
        AccountModel,
    )
    from swen.infrastructure.persistence.sqlalchemy.models.accounting.transaction_model import (  # NOQA: E501
        TransactionModel,
    )


class JournalEntryModel(Base, TimestampMixin):
    """Database model for journal entries (double-entry bookkeeping).

    Data Integrity Constraints:
    - Exactly one of debit_amount or credit_amount must be positive (XOR)
    - Both cannot be positive simultaneously
    - Both cannot be zero simultaneously
    - Amounts must be non-negative

    We duplicate the domain validation here to protect again bugs or corruption
    somewhere.
    """

    __tablename__ = "journal_entries"

    # Database-level constraints for data integrity
    __table_args__ = (
        # XOR constraint: exactly one of debit or credit must be positive
        # (debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0)
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR "
            "(debit_amount = 0 AND credit_amount > 0)",
            name="ck_journal_entry_xor_debit_credit",
        ),
        # Non-negative constraint (redundant with XOR but explicit)
        CheckConstraint(
            "debit_amount >= 0 AND credit_amount >= 0",
            name="ck_journal_entry_non_negative_amounts",
        ),
    )

    # Primary key (UUID from domain)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    # Foreign keys
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("accounting_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("accounting_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amounts (stored as positive values)
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Currency (inherited from account, but stored for auditing)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(
        "TransactionModel",
        back_populates="entries",
    )
    account: Mapped["AccountModel"] = relationship(
        "AccountModel",
        back_populates="journal_entries",
    )

    def __repr__(self) -> str:
        amount_type = "Debit" if self.debit_amount > 0 else "Credit"
        amount = self.debit_amount if self.debit_amount > 0 else self.credit_amount
        return (
            f"<JournalEntryModel(id={self.id}, "
            f"{amount_type}={amount}, account_id={self.account_id})>"
        )
