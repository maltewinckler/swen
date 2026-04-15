"""SQLAlchemy model for bank information (BLZ → name, BIC, etc.)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.shared.time import utc_now
from swen.infrastructure.persistence.sqlalchemy.models.base import Base


class BankInfoModel(Base):
    """Public bank metadata, populated at admin setup time."""

    __tablename__ = "bank_information"

    blz: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bic: Mapped[str | None] = mapped_column(String, nullable=True)
    organization: Mapped[str | None] = mapped_column(String, nullable=True)
    is_fints_capable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
