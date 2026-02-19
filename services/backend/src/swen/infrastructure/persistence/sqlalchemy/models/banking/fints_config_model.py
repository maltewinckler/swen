"""SQLAlchemy model for system-wide FinTS configuration."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class FinTSConfigModel(Base, TimestampMixin):
    """Database model for system-wide FinTS configuration.

    Uses a singleton pattern (id=1) to store a single system-wide
    configuration record containing the encrypted Product ID and
    the raw CSV institute directory data.
    """

    __tablename__ = "fints_configuration"

    __table_args__ = (
        CheckConstraint("id = 1", name="single_config_row"),
        Index("idx_fints_config_updated_at", "updated_at"),
    )

    # Singleton primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Encrypted Product ID
    product_id_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # CSV Data
    csv_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    csv_encoding: Mapped[str] = mapped_column(
        String(20), nullable=False, default="cp1252"
    )
    csv_upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    csv_file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_institute_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Audit fields (created_at and updated_at from TimestampMixin)
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FinTSConfigModel(id={self.id}, institutes={self.csv_institute_count})>"
        )
