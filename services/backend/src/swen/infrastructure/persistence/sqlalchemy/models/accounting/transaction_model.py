"""SQLAlchemy model for accounting transactions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from swen.infrastructure.persistence.sqlalchemy.models.base import (
    Base,
    TimestampMixin,
)

if TYPE_CHECKING:
    from swen.infrastructure.persistence.sqlalchemy.models.accounting.journal_entry_model import (  # NOQA: E501
        JournalEntryModel,
    )


class TransactionModel(Base, TimestampMixin):
    """Database model for accounting transactions."""

    __tablename__ = "accounting_transactions"

    __table_args__ = (
        # Index for user-scoped queries
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_user_date", "user_id", "date"),
        # Indexes for filtering
        Index("ix_transactions_source", "source"),
        Index("ix_transactions_source_iban", "source_iban"),
        Index("ix_transactions_counterparty_iban", "counterparty_iban"),
        Index("ix_transactions_is_internal_transfer", "is_internal_transfer"),
    )

    # Primary key (UUID from domain)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    # User ownership (required for multi-user)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Transaction details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Counterparty tracking
    counterparty: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    counterparty_iban: Mapped[str | None] = mapped_column(
        String(34),
        nullable=True,
        comment="IBAN of the sender/recipient",
    )

    # Transaction source and origin
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="Transaction origin: bank_import, manual, opening_balance, reversal",
    )
    source_iban: Mapped[str | None] = mapped_column(
        String(34),
        nullable=True,
        comment="IBAN of the source bank account (for bank imports)",
    )

    # Transfer tracking
    is_internal_transfer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a transfer between own accounts",
    )

    # Use transaction_metadata to avoid conflict with SQLAlchemy's metadata
    transaction_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # State
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Domain timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    entries: Mapped[list[JournalEntryModel]] = relationship(
        "JournalEntryModel",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="joined",  # Always load entries with transaction
    )

    def __repr__(self) -> str:
        return (
            f"<TransactionModel(id={self.id}, "
            f"description={self.description[:50]}, posted={self.is_posted})>"
        )
