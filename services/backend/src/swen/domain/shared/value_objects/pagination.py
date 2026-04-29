"""Pagination value object for repository queries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class Pagination(BaseModel):
    """Page-based pagination parameters.

    Attributes
    ----------
    page
        1-based page number.
    page_size
        Number of items per page.
    """

    model_config = ConfigDict(frozen=True)

    page: int = 1
    page_size: int = 50

    @field_validator("page")
    @classmethod
    def page_must_be_positive(cls, v: int) -> int:
        if v < 1:
            msg = f"page must be >= 1, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("page_size")
    @classmethod
    def page_size_must_be_positive(cls, v: int) -> int:
        if v < 1:
            msg = f"page_size must be >= 1, got {v}"
            raise ValueError(msg)
        return v

    @property
    def offset(self) -> int:
        """SQL offset derived from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL limit (alias for page_size)."""
        return self.page_size
