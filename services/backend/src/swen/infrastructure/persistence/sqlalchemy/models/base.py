"""SQLAlchemy base configuration."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from swen.domain.shared.time import utc_now


class Base(DeclarativeBase):
    """Base class for all database models."""


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps (utc_now)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
