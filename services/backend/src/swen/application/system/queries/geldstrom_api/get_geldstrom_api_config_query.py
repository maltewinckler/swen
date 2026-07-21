"""Query to get Geldstrom API configuration."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class GeldstromApiConfigDTO(BaseModel):
    """DTO for Geldstrom API configuration response."""

    model_config = ConfigDict(frozen=True)

    api_key_masked: str
    endpoint_url: str
    is_active: bool
    last_updated: datetime
    last_updated_by: str


class GetGeldstromApiConfigQuery:
    """Get current Geldstrom API configuration (admin only)."""

    def __init__(
        self,
        config_repository: GeldstromApiConfigRepository,
    ):
        self._repository = config_repository

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> GetGeldstromApiConfigQuery:
        return cls(
            config_repository=factory.geldstrom_api_config_repository(),
        )

    async def execute(self) -> GeldstromApiConfigDTO | None:
        """Get configuration with masked API key."""
        config = await self._repository.get_configuration()
        if not config:
            return None

        return GeldstromApiConfigDTO(
            api_key_masked=self._mask_api_key(config.api_key),
            endpoint_url=config.endpoint_url,
            is_active=config.is_active,
            last_updated=config.updated_at,
            last_updated_by=config.updated_by_id,
        )

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """Mask API key for display (show first 4 and last 4 chars)."""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return f"{api_key[:4]}...{api_key[-4:]}"
