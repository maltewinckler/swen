"""Query to get FinTS configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from swen.infrastructure.banking.fints_config_repository import (
    FinTSConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass(frozen=True)
class FinTSConfigDTO:
    """DTO for FinTS configuration response."""

    product_id_masked: str
    csv_institute_count: int
    csv_file_size_bytes: int
    csv_upload_timestamp: datetime
    updated_at: datetime
    updated_by_id: str


class GetFinTSConfigurationQuery:
    """Get current FinTS configuration (admin only)."""

    def __init__(
        self,
        config_repository: FinTSConfigRepository,
    ):
        self._repository = config_repository

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> GetFinTSConfigurationQuery:
        """Create query from repository factory."""
        return cls(
            config_repository=factory.fints_config_repository(),
        )

    async def execute(self) -> FinTSConfigDTO | None:
        """Get configuration with masked Product ID."""
        config = await self._repository.get_configuration()
        if not config:
            return None

        return FinTSConfigDTO(
            product_id_masked=self._mask_product_id(config.product_id),
            csv_institute_count=config.csv_institute_count,
            csv_file_size_bytes=config.csv_file_size_bytes,
            csv_upload_timestamp=config.csv_upload_timestamp,
            updated_at=config.updated_at,
            updated_by_id=config.updated_by_id,
        )

    @staticmethod
    def _mask_product_id(product_id: str) -> str:
        """Mask Product ID for display (show first 4 and last 4 chars)."""
        if len(product_id) <= 8:
            return "*" * len(product_id)
        return f"{product_id[:4]}...{product_id[-4:]}"
