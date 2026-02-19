"""DTOs for FinTS configuration API endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class UpdateProductIDRequest(BaseModel):
    """Request to update Product ID."""

    product_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="FinTS Product ID from Deutsche Kreditwirtschaft",
    )


class UploadCSVResponse(BaseModel):
    """Response after CSV upload."""

    message: str
    institute_count: int
    file_size_kb: int


class FinTSConfigResponse(BaseModel):
    """FinTS configuration details."""

    product_id_masked: str
    csv_institute_count: int
    csv_file_size_kb: int
    last_updated: datetime
    last_updated_by: str


class ConfigStatusResponse(BaseModel):
    """FinTS configuration status."""

    is_configured: bool
    message: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class SaveInitialConfigResponse(BaseModel):
    """Response after saving initial FinTS configuration."""

    message: str
    institute_count: int
    file_size_kb: int
