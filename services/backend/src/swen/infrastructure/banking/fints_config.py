"""Domain transfer objects for FinTS configuration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FinTSConfig:
    """Represents system-wide FinTS configuration.

    This is a simple DTO for transferring configuration data
    between infrastructure and application layers.
    """

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
    updated_by_email: str | None = None  # Populated via join


@dataclass(frozen=True)
class FinTSConfigStatus:
    """Configuration status for display and validation."""

    is_configured: bool
    has_product_id: bool = False
    has_csv: bool = False
    institute_count: int = 0


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    error: str | None = None


@dataclass(frozen=True)
class CSVValidationResult:
    """Result of CSV validation."""

    is_valid: bool
    institute_count: int = 0
    file_size_bytes: int = 0
    error: str | None = None


@dataclass(frozen=True)
class UploadResult:
    """Result of CSV upload operation."""

    institute_count: int
    file_size_bytes: int
