"""Domain transfer objects for FinTS configuration."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FinTSConfig(BaseModel):
    """Represents system-wide FinTS configuration.

    This is a simple DTO for transferring configuration data
    between infrastructure and application layers.
    """

    model_config = ConfigDict(frozen=True)

    product_id: str  # Decrypted
    csv_content: bytes
    csv_encoding: str
    csv_upload_timestamp: datetime
    csv_file_size_bytes: int
    csv_institute_count: int
    created_at: datetime
    created_by_id: str
    updated_at: datetime
    updated_by_id: str
    is_active: bool = True
    updated_by_email: str | None = None  # Populated via join


class FinTSConfigStatus(BaseModel):
    """Configuration status for display and validation."""

    model_config = ConfigDict(frozen=True)

    is_configured: bool
    is_active: bool = False
    has_product_id: bool = False
    has_csv: bool = False
    institute_count: int = 0


class ValidationResult(BaseModel):
    """Result of a validation operation."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool
    error: str | None = None


class CSVValidationResult(BaseModel):
    """Result of CSV validation."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool
    institute_count: int = 0
    file_size_bytes: int = 0
    error: str | None = None


class UpdateConfigResult(BaseModel):
    """Result of a local FinTS configuration update."""

    model_config = ConfigDict(frozen=True)

    institute_count: int | None = None
    file_size_bytes: int | None = None
