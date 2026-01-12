"""SQLAlchemy model for CounterAccountRule value object.

Note: The table name remains "categorization_rules" to avoid database migration.
The class and code terminology has been updated to align with our Ubiquitous Language.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.integration.value_objects import PatternType, RuleSource
from swen.infrastructure.persistence.sqlalchemy.models.base import Base, TimestampMixin


class CounterAccountRuleModel(Base, TimestampMixin):
    """
    SQLAlchemy model for persisting CounterAccountRule value objects.

    Stores rules for automatic transaction counter-account resolution.
    Each user has their own set of counter-account rules.

    Note: Table name kept as "categorization_rules" for backward compatibility.
    """

    # Keep old table name to avoid migration
    __tablename__ = "categorization_rules"

    __table_args__ = (
        Index("ix_rules_user_id", "user_id"),
        Index("ix_rules_user_priority", "user_id", "priority"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)

    # User ownership (required for multi-user)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Pattern configuration
    pattern_type: Mapped[PatternType] = mapped_column(
        SQLEnum(PatternType),
        index=True,
    )
    pattern_value: Mapped[str] = mapped_column(String(500))

    # Target counter-account (column name kept for backward compatibility)
    counter_account_id: Mapped[UUID] = mapped_column(
        "category_account_id",  # Keep old column name to avoid migration
        index=True,
    )

    # Rule metadata
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    source: Mapped[RuleSource] = mapped_column(
        SQLEnum(RuleSource),
        default=RuleSource.USER_CREATED,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Usage statistics
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    last_matched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<CounterAccountRuleModel(id={self.id}, "
            f"pattern_type={self.pattern_type.value}, "
            f"pattern_value={self.pattern_value[:30]})>"
        )
