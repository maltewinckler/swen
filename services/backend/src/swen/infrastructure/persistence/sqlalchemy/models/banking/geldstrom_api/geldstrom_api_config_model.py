"""SQLAlchemy model for system-wide Geldstrom API configuration."""

from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class GeldstromApiConfigModel(Base, TimestampMixin):
    """Database model for system-wide Geldstrom API configuration.

    Uses a singleton pattern (id=1) to store a single system-wide
    configuration record containing the encrypted API key and
    the Geldstrom API endpoint URL.
    """

    __tablename__ = "geldstrom_api_configuration"

    __table_args__ = (
        CheckConstraint("id = 1", name="single_geldstrom_config_row"),
        Index("idx_geldstrom_api_config_updated_at", "updated_at"),
    )

    # Singleton primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Encrypted API key
    api_key_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    encryption_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # API endpoint
    endpoint_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Provider active flag
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

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
            f"<GeldstromApiConfigModel("
            f"id={self.id}, "
            f"endpoint={self.endpoint_url}, "
            f"active={self.is_active})>"
        )
