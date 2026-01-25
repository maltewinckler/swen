"""Noise model domain model."""

from pydantic import BaseModel, Field


class NoiseData(BaseModel):
    """User's noise model data (IDF token frequencies)."""

    token_frequencies: dict[str, int] = Field(default_factory=dict)
    document_count: int = 0
