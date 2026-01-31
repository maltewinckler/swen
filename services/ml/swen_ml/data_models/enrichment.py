"""Enrichment cache domain model."""

from datetime import datetime

from pydantic import BaseModel, Field


class Enrichment(BaseModel):
    """Cached search enrichment result."""

    query: str
    enrichment_text: str
    source_urls: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    expires_at: datetime | None = None
    hit_count: int = 0
