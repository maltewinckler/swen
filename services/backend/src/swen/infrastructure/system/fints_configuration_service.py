"""Service for FinTS configuration management and validation."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from uuid import UUID

from swen.domain.shared.exceptions import ConflictError
from swen.domain.shared.time import utc_now
from swen.infrastructure.banking.fints_config import (
    CSVValidationResult,
    FinTSConfig,
    FinTSConfigStatus,
    UploadResult,
    ValidationResult,
)
from swen.infrastructure.banking.fints_config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.banking.fints_institute_directory import (
    invalidate_fints_directory_cache,
)

logger = logging.getLogger(__name__)

# CSV column indices (0-based) - same as FinTSInstituteDirectory
COL_BLZ = 1
COL_PIN_TAN_URL = 24

# Limits
MAX_CSV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class FinTSConfigurationService:
    """Orchestrates FinTS configuration operations.

    Handles validation, CSV parsing verification, and coordination
    between the repository and in-memory caches.
    """

    def __init__(
        self,
        repository: FinTSConfigRepository,
    ):
        self._repository = repository

    async def get_configuration_status(self) -> FinTSConfigStatus:
        """Get current configuration status for admin display."""
        config = await self._repository.get_configuration()

        if config is None:
            return FinTSConfigStatus(is_configured=False)

        return FinTSConfigStatus(
            is_configured=True,
            has_product_id=bool(config.product_id),
            has_csv=bool(config.csv_content),
            institute_count=config.csv_institute_count,
        )

    def validate_product_id(self, product_id: str) -> ValidationResult:
        """Validate Product ID format."""
        if not product_id or not product_id.strip():
            return ValidationResult(
                is_valid=False,
                error="Product ID cannot be empty",
            )

        product_id = product_id.strip()

        if len(product_id) > 100:
            return ValidationResult(
                is_valid=False,
                error="Product ID must be 100 characters or fewer",
            )

        return ValidationResult(is_valid=True)

    def validate_csv(self, csv_content: bytes) -> CSVValidationResult:  # noqa: PLR0911
        """Validate CSV structure and content."""
        if not csv_content:
            return CSVValidationResult(
                is_valid=False,
                error="CSV file is empty",
            )

        file_size = len(csv_content)

        if file_size > MAX_CSV_SIZE_BYTES:
            return CSVValidationResult(
                is_valid=False,
                file_size_bytes=file_size,
                error=f"CSV file too large ({file_size // 1024}KB). Max is 10MB.",
            )

        # Try to parse as CP1252
        try:
            text = csv_content.decode("cp1252")
        except (UnicodeDecodeError, ValueError):
            return CSVValidationResult(
                is_valid=False,
                file_size_bytes=file_size,
                error="CSV file is not valid CP1252 encoded text",
            )

        # Parse CSV and count valid institutes
        try:
            reader = csv.reader(StringIO(text), delimiter=";")

            # Skip header row
            try:
                next(reader)
            except StopIteration:
                return CSVValidationResult(
                    is_valid=False,
                    file_size_bytes=file_size,
                    error="CSV file is empty (no header row)",
                )

            institute_count = 0
            for row in reader:
                if len(row) > COL_PIN_TAN_URL:
                    blz = row[COL_BLZ].strip()
                    url = row[COL_PIN_TAN_URL].strip()
                    if (
                        blz
                        and url
                        and blz.isdigit()
                        and len(blz) == 8
                        and url.startswith("http")
                    ):
                        institute_count += 1

            if institute_count == 0:
                return CSVValidationResult(
                    is_valid=False,
                    file_size_bytes=file_size,
                    error="No valid institute entries found in CSV",
                )

            return CSVValidationResult(
                is_valid=True,
                institute_count=institute_count,
                file_size_bytes=file_size,
            )

        except csv.Error as e:
            return CSVValidationResult(
                is_valid=False,
                file_size_bytes=file_size,
                error=f"CSV parsing error: {e}",
            )

    async def update_product_id(
        self,
        product_id: str,
        admin_user_id: UUID,
    ) -> None:
        """Update Product ID with validation."""
        validation = self.validate_product_id(product_id)
        if not validation.is_valid:
            msg = f"Invalid Product ID: {validation.error}"
            raise ValueError(msg)

        await self._repository.update_product_id(
            product_id=product_id.strip(),
            admin_user_id=admin_user_id,
        )

        logger.info("Product ID updated by admin %s", admin_user_id)

    async def upload_csv(
        self,
        csv_content: bytes,
        admin_user_id: UUID,
    ) -> UploadResult:
        """Upload and validate CSV, updating configuration."""
        validation = self.validate_csv(csv_content)
        if not validation.is_valid:
            msg = f"Invalid CSV: {validation.error}"
            raise ValueError(msg)

        await self._repository.update_csv(
            csv_content=csv_content,
            encoding="cp1252",
            institute_count=validation.institute_count,
            admin_user_id=admin_user_id,
        )

        # Invalidate cached directory so next lookup uses new CSV
        invalidate_fints_directory_cache()

        logger.info(
            "CSV uploaded by admin %s: %d institutes",
            admin_user_id,
            validation.institute_count,
        )

        return UploadResult(
            institute_count=validation.institute_count,
            file_size_bytes=validation.file_size_bytes,
        )

    async def save_initial_configuration(
        self,
        product_id: str,
        csv_content: bytes,
        admin_user_id: UUID,
    ) -> FinTSConfig:
        """Save FinTS configuration (Product ID + CSV). Only creates if none exists."""
        existing = await self._repository.get_configuration()
        if existing is not None:
            msg = "FinTS configuration already exists. Use the update endpoints."
            raise ConflictError(msg)

        # Validate both
        pid_validation = self.validate_product_id(product_id)
        if not pid_validation.is_valid:
            msg = f"Invalid Product ID: {pid_validation.error}"
            raise ValueError(msg)

        csv_validation = self.validate_csv(csv_content)
        if not csv_validation.is_valid:
            msg = f"Invalid CSV: {csv_validation.error}"
            raise ValueError(msg)

        now = utc_now()
        config = FinTSConfig(
            product_id=product_id.strip(),
            csv_content=csv_content,
            csv_encoding="cp1252",
            csv_upload_timestamp=now,
            csv_file_size_bytes=csv_validation.file_size_bytes,
            csv_institute_count=csv_validation.institute_count,
            created_at=now,
            created_by_id=str(admin_user_id),
            updated_at=now,
            updated_by_id=str(admin_user_id),
        )

        await self._repository.save_configuration(config, admin_user_id)

        # Invalidate cached directory so next lookup uses new CSV
        invalidate_fints_directory_cache()

        logger.info(
            "Initial FinTS configuration saved by admin %s: %d institutes",
            admin_user_id,
            csv_validation.institute_count,
        )

        return config
