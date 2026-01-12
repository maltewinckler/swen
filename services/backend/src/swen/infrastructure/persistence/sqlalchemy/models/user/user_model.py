"""SQLAlchemy model for User aggregate."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    """
    SQLAlchemy model for persisting User aggregates.

    This model stores user identity and all preference settings.
    Preferences are stored as individual columns for easy querying
    and updating. Dashboard settings use JSON for flexibility.

    User ID is computed deterministically from email (UUID5), so:
    - email is required (NOT NULL)
    - email is unique (ensures no duplicate registrations)
    - id is derived from email (but stored for foreign key references)

    Table: users
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Sync settings
    auto_post_transactions: Mapped[bool] = mapped_column(default=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Display settings
    show_draft_transactions: Mapped[bool] = mapped_column(default=True)
    default_date_range_days: Mapped[int] = mapped_column(default=30)

    # Dashboard settings (JSON for flexibility)
    # enabled_widgets: list of widget IDs in display order
    # widget_settings: dict mapping widget ID to settings dict
    dashboard_enabled_widgets: Mapped[Optional[list[Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    dashboard_widget_settings: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # AI settings
    ai_enabled: Mapped[bool] = mapped_column(default=True)
    ai_model_name: Mapped[str] = mapped_column(String(100), default="qwen2.5:3b")
    ai_min_confidence: Mapped[float] = mapped_column(default=0.7)

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email})>"
