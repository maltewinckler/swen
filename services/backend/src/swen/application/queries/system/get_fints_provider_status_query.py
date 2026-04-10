"""Query to get the overall FinTS provider status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.infrastructure.banking.geldstrom.fints_config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass(frozen=True)
class FintsProviderStatusDTO:
    """DTO for overall FinTS provider status."""

    local_configured: bool
    local_active: bool
    api_configured: bool
    api_active: bool
    active_provider: str | None  # "local", "api", or None


class GetFintsProviderStatusQuery:
    """Get which FinTS provider is active and configured."""

    def __init__(
        self,
        fints_config_repo: FinTSConfigRepository,
        geldstrom_api_config_repo: GeldstromApiConfigRepository,
    ):
        self._fints_repo = fints_config_repo
        self._api_repo = geldstrom_api_config_repo

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> GetFintsProviderStatusQuery:
        return cls(
            fints_config_repo=factory.fints_config_repository(),
            geldstrom_api_config_repo=(factory.geldstrom_api_config_repository()),
        )

    async def execute(self) -> FintsProviderStatusDTO:
        """Get provider status."""
        local_configured = await self._fints_repo.exists()
        local_active = await self._fints_repo.is_active()
        api_configured = await self._api_repo.exists()
        api_active = await self._api_repo.is_active()

        active_provider: str | None = None
        if api_active:
            active_provider = "api"
        elif local_active:
            active_provider = "local"

        return FintsProviderStatusDTO(
            local_configured=local_configured,
            local_active=local_active,
            api_configured=api_configured,
            api_active=api_active,
            active_provider=active_provider,
        )
