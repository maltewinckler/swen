"""SQLAlchemy model for user authentication credentials.

This model stores password hashes and authentication metadata.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.shared.time import utc_now
from swen_auth.persistence.sqlalchemy.base import AuthBase


class UserCredentialModel(AuthBase):
    """
    SQLAlchemy model for user authentication credentials.

    This stores password hashes and security metadata separately from
    the main User model. Each user has at most one credential record.

    Security features:
    - failed_login_attempts: Tracks consecutive failed logins
    - locked_until: Account lockout timestamp
    - last_login_at: Audit trail for login activity

    Table: user_credentials
    """

    __tablename__ = "user_credentials"

    # Primary key
    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # User identifier (no FK to stay decoupled from user table)
    # The consuming application manages the relationship
    user_id: Mapped[str] = mapped_column(
        String(36),  # UUID string format
        unique=True,
        nullable=False,
        index=True,
    )

    # Password hash (bcrypt format, ~60 chars)
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Security metadata
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Audit timestamps
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
        """String representation for debugging."""
        return f"<UserCredentialModel(id={self.id}, user_id={self.user_id})>"

    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until is None:
            return False
        return utc_now() < self.locked_until
