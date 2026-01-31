"""SQLAlchemy table definitions for ML storage.

These are thin persistence mappings. Domain logic lives in Pydantic models.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnchorTable(Base):
    """Account anchor embeddings table."""

    __tablename__ = "anchor_embeddings"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[UUID] = mapped_column(primary_key=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExampleTable(Base):
    """Training examples table."""

    __tablename__ = "user_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NoiseTable(Base):
    """User noise models table."""

    __tablename__ = "user_noise_models"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    token_frequencies: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EnrichmentCacheTable(Base):
    """Search enrichment cache table."""

    __tablename__ = "enrichment_cache"

    query_hash: Mapped[str] = mapped_column(String(32), primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    enrichment_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_enrichment_cache_expires", "expires_at"),)
