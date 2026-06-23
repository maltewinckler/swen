"""Common schemas shared across API endpoints."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code for programmatic handling")
    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="When the error occurred",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "Resource not found", "code": "NOT_FOUND"},
        },
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Base schema for paginated responses."""

    items: list[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        """Create a paginated response."""
        pages = (total + page_size - 1) // page_size if total > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
