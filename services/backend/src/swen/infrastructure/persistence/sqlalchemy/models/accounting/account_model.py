"""SQLAlchemy model for accounting accounts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from swen.infrastructure.persistence.sqlalchemy.models.base import (
    Base,
    TimestampMixin,
)

if TYPE_CHECKING:
    from swen.infrastructure.persistence.sqlalchemy.models.accounting.journal_entry_model import (  # NOQA: E501
        JournalEntryModel,
    )


class AccountModel(Base, TimestampMixin):
    """Database model for accounting accounts."""

    __tablename__ = "accounting_accounts"

    __table_args__ = (
        # Composite index for user-scoped queries
        Index("ix_accounts_user_id", "user_id"),
        Index("ix_accounts_user_account_number", "user_id", "account_number"),
        Index("ix_accounts_user_iban", "user_id", "iban"),
        # Uniqueness constraints (stabilize identity semantics at persistence layer)
        UniqueConstraint(
            "user_id",
            "account_number",
            name="uq_accounts_user_account_number",
        ),
        UniqueConstraint("user_id", "iban", name="uq_accounts_user_iban"),
    )

    # Primary key (UUID from domain)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    # User ownership (required for multi-user)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Account identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    iban: Mapped[Optional[str]] = mapped_column(String(34), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Account properties
    default_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Hierarchy support
    parent_id: Mapped[Optional[UUID]] = mapped_column(Uuid, nullable=True, index=True)

    # Domain timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    journal_entries: Mapped[list[JournalEntryModel]] = relationship(
        "JournalEntryModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AccountModel(id={self.id}, name={self.name}, type={self.account_type})>"
        )
