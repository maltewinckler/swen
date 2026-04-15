"""Service for FinTS configuration management and validation."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from uuid import UUID

from swen.domain.shared.time import utc_now
from swen.infrastructure.banking.local_fints.models.config import (
    CSVValidationResult,
    FinTSConfig,
    FinTSConfigStatus,
    UpdateConfigResult,
    ValidationResult,
)
from swen.infrastructure.banking.local_fints.repositories.config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.banking.local_fints.value_objects.institute_directory import (
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

    async def update_configuration(
        self,
        admin_user_id: UUID,
        product_id: str | None = None,
        csv_content: bytes | None = None,
    ) -> UpdateConfigResult:
        """Create or update local FinTS configuration (upsert).

        At least one of ``product_id`` or ``csv_content`` must be provided.
        On first call (no config exists yet) both are required.  On subsequent
        calls each field is patched independently when supplied.
        """
        if product_id is None and csv_content is None:
            msg = "At least one of product_id or csv_content must be provided"
            raise ValueError(msg)

        csv_validation = self._validate_inputs(product_id, csv_content)
        exists = await self._repository.exists()

        if not exists:
            await self._create_configuration(
                admin_user_id, product_id, csv_content, csv_validation
            )
        else:
            await self._patch_configuration(
                admin_user_id, product_id, csv_content, csv_validation
            )

        if csv_content is not None:
            invalidate_fints_directory_cache()

        logger.info(
            "Local FinTS configuration updated by admin %s (product_id=%s, csv=%s)",
            admin_user_id,
            product_id is not None,
            csv_content is not None,
        )

        return UpdateConfigResult(
            institute_count=csv_validation.institute_count if csv_validation else None,
            file_size_bytes=csv_validation.file_size_bytes if csv_validation else None,
        )

    def _validate_inputs(
        self,
        product_id: str | None,
        csv_content: bytes | None,
    ) -> CSVValidationResult | None:
        """Validate provided fields and return CSV validation result if applicable."""
        if product_id is not None:
            pid_result = self.validate_product_id(product_id)
            if not pid_result.is_valid:
                msg = f"Invalid Product ID: {pid_result.error}"
                raise ValueError(msg)

        if csv_content is None:
            return None

        csv_result = self.validate_csv(csv_content)
        if not csv_result.is_valid:
            msg = f"Invalid CSV: {csv_result.error}"
            raise ValueError(msg)
        return csv_result

    async def _create_configuration(
        self,
        admin_user_id: UUID,
        product_id: str | None,
        csv_content: bytes | None,
        csv_validation: CSVValidationResult | None,
    ) -> None:
        """Save the initial configuration (both fields required)."""
        if product_id is None:
            msg = "Product ID is required for initial configuration"
            raise ValueError(msg)
        if csv_content is None or csv_validation is None:
            msg = "Institute CSV is required for initial configuration"
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

    async def _patch_configuration(
        self,
        admin_user_id: UUID,
        product_id: str | None,
        csv_content: bytes | None,
        csv_validation: CSVValidationResult | None,
    ) -> None:
        """Patch only the supplied fields on an existing configuration."""
        if product_id is not None:
            await self._repository.update_product_id(
                product_id=product_id.strip(),
                admin_user_id=admin_user_id,
            )
        if csv_content is not None and csv_validation is not None:
            await self._repository.update_csv(
                csv_content=csv_content,
                encoding="cp1252",
                institute_count=csv_validation.institute_count,
                admin_user_id=admin_user_id,
            )
