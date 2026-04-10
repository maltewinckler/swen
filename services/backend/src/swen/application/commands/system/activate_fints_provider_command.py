"""Command to activate a FinTS provider (local or API)."""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from swen.infrastructure.banking.geldstrom.fints_config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory

logger = logging.getLogger(__name__)


class FintsProviderMode(str, Enum):
    """Which FinTS provider to activate."""

    LOCAL = "local"
    API = "api"


class ProviderNotConfiguredError(Exception):
    """Raised when trying to activate a provider that isn't configured."""


class ActivateFintsProviderCommand:
    """Activate the specified FinTS provider and deactivate the other."""

    def __init__(
        self,
        fints_config_repo: FinTSConfigRepository,
        geldstrom_api_config_repo: GeldstromApiConfigRepository,
        admin_user_id: UUID,
    ):
        self._fints_repo = fints_config_repo
        self._api_repo = geldstrom_api_config_repo
        self._admin_user_id = admin_user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> ActivateFintsProviderCommand:
        return cls(
            fints_config_repo=factory.fints_config_repository(),
            geldstrom_api_config_repo=(factory.geldstrom_api_config_repository()),
            admin_user_id=factory.current_user.user_id,
        )

    async def execute(self, mode: FintsProviderMode) -> None:
        """Activate the given provider, deactivate the other."""
        if mode == FintsProviderMode.LOCAL:
            if not await self._fints_repo.exists():
                msg = (
                    "Local FinTS is not configured. "
                    "Upload a Product ID and institute CSV first."
                )
                raise ProviderNotConfiguredError(msg)
            await self._api_repo.deactivate(self._admin_user_id)
            await self._fints_repo.activate(self._admin_user_id)
            logger.info("Activated local FinTS provider")
        else:
            if not await self._api_repo.exists():
                msg = (
                    "Geldstrom API is not configured. "
                    "Save an API key and endpoint first."
                )
                raise ProviderNotConfiguredError(msg)
            await self._fints_repo.deactivate(self._admin_user_id)
            await self._api_repo.activate(self._admin_user_id)
            logger.info("Activated Geldstrom API provider")
