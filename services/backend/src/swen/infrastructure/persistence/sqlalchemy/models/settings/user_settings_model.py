"""SQLAlchemy model for UserSettings aggregate."""

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class UserSettingsModel(Base, TimestampMixin):
    """SQLAlchemy model for persisting UserSettings aggregates."""

    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    auto_post_transactions: Mapped[bool] = mapped_column(default=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    show_draft_transactions: Mapped[bool] = mapped_column(default=True)
    default_date_range_days: Mapped[int] = mapped_column(default=30)
    dashboard_enabled_widgets: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    dashboard_widget_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    ai_enabled: Mapped[bool] = mapped_column(default=True)
    ai_model_name: Mapped[str] = mapped_column(String(100), default="qwen2.5:3b")
    ai_min_confidence: Mapped[float] = mapped_column(default=0.7)

    def __repr__(self) -> str:
        return f"<UserSettingsModel(user_id={self.user_id})>"
