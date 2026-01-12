"""SQLAlchemy model for bank transactions."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from swen.infrastructure.persistence.sqlalchemy.models.base import (
    Base,
    TimestampMixin,
)

if TYPE_CHECKING:
    from swen.infrastructure.persistence.sqlalchemy.models.banking.bank_account_model import (  # NOQA: E501
        BankAccountModel,
    )


class BankTransactionModel(Base, TimestampMixin):
    """Database model for bank transactions.

    Deduplication Strategy:
    - identity_hash: Computed hash of transaction content (date, amount, purpose, etc.)
    - hash_sequence: Sequence number for identical transactions (1, 2, 3...)
    - Unique constraint on (account_id, identity_hash, hash_sequence)

    This allows multiple identical transactions (e.g., two refunds of 3.10€ on the
    same day with the same purpose) to be stored with different sequence numbers.
    """

    __tablename__ = "bank_transactions"

    # Primary key (random UUID, not deterministic)
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key to bank account
    account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Deduplication fields
    identity_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Hash of transaction content for grouping identical transactions",
    )
    hash_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Sequence number for identical transactions (1, 2, 3...)",
    )

    # Transaction dates
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Amount and currency
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Transaction description
    purpose: Mapped[str] = mapped_column(Text, nullable=False)

    # Counterparty information
    applicant_name: Mapped[Optional[str]] = mapped_column(String(255))
    applicant_iban: Mapped[Optional[str]] = mapped_column(String(34), index=True)
    applicant_bic: Mapped[Optional[str]] = mapped_column(String(11))

    # References
    bank_reference: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    customer_reference: Mapped[Optional[str]] = mapped_column(String(255))
    end_to_end_reference: Mapped[Optional[str]] = mapped_column(String(255))
    mandate_reference: Mapped[Optional[str]] = mapped_column(String(255))
    creditor_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Transaction metadata
    transaction_code: Mapped[Optional[str]] = mapped_column(String(10))
    posting_text: Mapped[Optional[str]] = mapped_column(String(255))

    # Categorization (will be used later for accounting integration)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    is_categorized: Mapped[bool] = mapped_column(default=False)

    # Import tracking
    is_imported: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether this transaction has been imported to accounting",
    )

    # Relationship
    account: Mapped["BankAccountModel"] = relationship(
        "BankAccountModel",
        back_populates="transactions",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_account_date", "account_id", "booking_date"),
        # Unique constraint: same identity hash + sequence cannot exist twice
        Index(
            "idx_bank_tx_hash_sequence",
            "account_id",
            "identity_hash",
            "hash_sequence",
            unique=True,
        ),
        # Index for finding un-imported transactions
        Index("idx_account_not_imported", "account_id", "is_imported"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankTransactionModel(id={self.id}, "
            f"date={self.booking_date}, amount={self.amount})>"
        )
