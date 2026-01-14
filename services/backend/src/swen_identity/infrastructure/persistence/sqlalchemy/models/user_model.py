"""SQLAlchemy model for User aggregate."""

from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    """SQLAlchemy model for persisting User aggregates.

    Contains only identity data. Settings/preferences are stored separately
    in the user_settings table (managed by swen.domain.settings).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email}, role={self.role})>"
