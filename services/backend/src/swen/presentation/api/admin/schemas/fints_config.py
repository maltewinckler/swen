"""DTOs for local FinTS configuration API endpoints."""

from datetime import datetime

from pydantic import BaseModel


class FinTSConfigResponse(BaseModel):
    """Local FinTS configuration details."""

    product_id_masked: str
    csv_institute_count: int
    csv_file_size_kb: int
    last_updated: datetime
    last_updated_by: str


class ConfigStatusResponse(BaseModel):
    """Local FinTS configuration status."""

    is_configured: bool
    message: str


class UpdateLocalFinTSConfigResponse(BaseModel):
    """Response after creating or updating local FinTS configuration."""

    message: str
    institute_count: int | None = None
    file_size_kb: int | None = None
