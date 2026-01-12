"""SQLAlchemy model for bank accounts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from swen.infrastructure.persistence.sqlalchemy.models.base import (
    Base,
    TimestampMixin,
)

if TYPE_CHECKING:
    from swen.infrastructure.persistence.sqlalchemy.models.banking.bank_transaction_model import (  # NOQA: E501
        BankTransactionModel,
    )


class BankAccountModel(Base, TimestampMixin):
    """Database model for bank accounts."""

    __tablename__ = "bank_accounts"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User association
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Account identification
    iban: Mapped[str] = mapped_column(String(34), nullable=False, index=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(50))
    blz: Mapped[str] = mapped_column(String(8), nullable=False)
    bic: Mapped[Optional[str]] = mapped_column(String(11))

    # Account details
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    account_type: Mapped[Optional[str]] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Balance information
    balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    balance_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Sync tracking
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    transactions: Mapped[list[BankTransactionModel]] = relationship(
        "BankTransactionModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    # Unique constraint: one IBAN per user
    __table_args__ = (Index("idx_user_iban", "user_id", "iban", unique=True),)

    def __repr__(self) -> str:
        return (
            f"<BankAccountModel(id={self.id}, "
            f"iban={self.iban}, owner={self.owner_name})>"
        )
