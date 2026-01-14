"""SQLAlchemy model for user authentication credentials."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.shared.time import utc_now
from swen_identity.infrastructure.persistence.sqlalchemy.base import IdentityBase


class UserCredentialModel(IdentityBase):
    """SQLAlchemy model for user authentication credentials."""

    __tablename__ = "user_credentials"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<UserCredentialModel(id={self.id}, user_id={self.user_id})>"

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return utc_now() < self.locked_until
