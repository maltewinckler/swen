"""SQLAlchemy model for FinTS endpoint URLs."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from swen.domain.shared.time import utc_now
from swen.infrastructure.persistence.sqlalchemy.models.base import Base


class FinTSEndpointModel(Base):
    """FinTS server URL for a bank, keyed by BLZ.

    This is an infrastructure concern, only the local FinTS adapter
    needs endpoint URLs. The Geldstrom API resolves endpoints internally.
    """

    __tablename__ = "fints_endpoints"

    blz: Mapped[str] = mapped_column(String(8), primary_key=True)
    endpoint_url: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
