"""SQLAlchemy model for AccountMapping entity."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class AccountMappingModel(Base, TimestampMixin):
    """
    SQLAlchemy model for persisting AccountMapping entities.

    Links bank accounts (IBAN) to accounting accounts for transaction import.
    Each user can have their own mapping for the same IBAN.
    """

    __tablename__ = "account_mappings"

    __table_args__ = (
        # IBAN is unique per user (not globally unique)
        UniqueConstraint("user_id", "iban", name="uq_mapping_user_iban"),
        Index("ix_mappings_user_id", "user_id"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)

    # User ownership (required for multi-user)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Bank account identification (unique per user)
    iban: Mapped[str] = mapped_column(String(34), index=True)

    # Accounting account reference
    accounting_account_id: Mapped[UUID] = mapped_column(index=True)

    # Display information
    account_name: Mapped[str] = mapped_column(String(255))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<AccountMappingModel(id={self.id}, iban={self.iban}, "
            f"account_name={self.account_name})>"
        )
