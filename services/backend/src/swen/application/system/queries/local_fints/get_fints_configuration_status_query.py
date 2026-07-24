"""Query to check FinTS configuration status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from swen.infrastructure.banking.local_fints.repositories.config_repository import (
    FinTSConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class FinTSConfigStatusDTO(BaseModel):
    """DTO for configuration status."""

    model_config = ConfigDict(frozen=True)

    is_configured: bool
    message: str


class GetFinTSConfigurationStatusQuery:
    """Check if FinTS is configured (for health checks and onboarding)."""

    def __init__(
        self,
        config_repository: FinTSConfigRepository,
    ):
        self._repository = config_repository

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> GetFinTSConfigurationStatusQuery:
        """Create query from repository factory."""
        return cls(
            config_repository=factory.fints_config_repository(),
        )

    async def execute(self) -> FinTSConfigStatusDTO:
        """Get configuration status."""
        exists = await self._repository.exists()

        return FinTSConfigStatusDTO(
            is_configured=exists,
            message="FinTS configured" if exists else "FinTS not configured",
        )
