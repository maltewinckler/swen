"""Command to update FinTS Product ID."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.infrastructure.system.fints_configuration_service import (
    FinTSConfigurationService,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory

logger = logging.getLogger(__name__)


class UpdateFinTSProductIDCommand:
    """Update the system-wide FinTS Product ID."""

    def __init__(
        self,
        config_service: FinTSConfigurationService,
        admin_user_id: UUID,
    ):
        self._service = config_service
        self._admin_user_id = admin_user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> UpdateFinTSProductIDCommand:
        """Create command from repository factory."""
        return cls(
            config_service=FinTSConfigurationService(
                repository=factory.fints_config_repository(),
            ),
            admin_user_id=factory.current_user.user_id,
        )

    async def execute(self, product_id: str) -> None:
        """Update Product ID with validation."""
        await self._service.update_product_id(
            product_id=product_id,
            admin_user_id=self._admin_user_id,
        )

        logger.info("Product ID updated by admin %s", self._admin_user_id)
