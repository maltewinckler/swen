"""SQLAlchemy model for stored credentials."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class StoredCredentialModel(Base, TimestampMixin):
    """SQLAlchemy model for encrypted bank credentials."""

    __tablename__ = "stored_credentials"

    __table_args__ = (
        Index("ix_credentials_user_id", "user_id"),
        Index("ix_credentials_user_blz", "user_id", "blz"),
    )

    # Primary Key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Ownership (required for multi-user)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Bank Identification (plaintext - not sensitive)
    blz: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)

    # Encrypted Credentials (binary blobs)
    username_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    pin_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Security Metadata
    encryption_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # User-Friendly Metadata
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # TAN Settings (plaintext - not sensitive, needed for bank connection)
    tan_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tan_medium: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Domain-specific timestamp
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"StoredCredentialModel(id={self.id}, user_id={self.user_id}, "
            f"blz={self.blz}, label={self.label})"
        )
