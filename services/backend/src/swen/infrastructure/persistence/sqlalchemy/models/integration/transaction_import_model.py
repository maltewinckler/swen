"""SQLAlchemy model for TransactionImport entity."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.integration.value_objects import ImportStatus
from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class TransactionImportModel(Base, TimestampMixin):
    """
    SQLAlchemy model for persisting TransactionImport entities.

    Tracks bank transaction import history and links to accounting transactions.
    Each user has their own import history (same bank transaction can be imported
    by different users).

    Deduplication Strategy:
    - bank_transaction_id: FK to bank_transactions table (unique per user)
    - Uses hash + sequence in bank_transactions to handle identical transactions

    Database Constraints:
    - If status = 'success', accounting_transaction_id must not be NULL
    - If status = 'failed', error_message must not be NULL
    """

    __tablename__ = "transaction_imports"

    __table_args__ = (
        CheckConstraint(
            "(status != 'success' OR accounting_transaction_id IS NOT NULL)",
            name="check_success_has_transaction_id",
        ),
        CheckConstraint(
            "(status != 'failed' OR error_message IS NOT NULL)",
            name="check_failed_has_error_message",
        ),
        # Bank transaction ID is unique per user
        UniqueConstraint(
            "user_id",
            "bank_transaction_id",
            name="uq_import_user_bank_tx",
        ),
        Index("ix_imports_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Reference to stored bank transaction (for deduplication)
    bank_transaction_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("bank_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[ImportStatus] = mapped_column(
        SQLEnum(
            ImportStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=ImportStatus.PENDING,
        index=True,
    )

    accounting_transaction_id: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        index=True,
    )

    # Error information (if failed)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Domain-specific timestamp (when import succeeded)
    imported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<TransactionImportModel(id={self.id}, "
            f"status={self.status.value}, "
            f"bank_tx={self.bank_transaction_id})>"
        )
