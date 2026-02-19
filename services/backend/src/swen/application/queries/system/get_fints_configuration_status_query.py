"""Query to check FinTS configuration status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.infrastructure.banking.fints_config_repository import (
    FinTSConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass(frozen=True)
class FinTSConfigStatusDTO:
    """DTO for configuration status."""

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
