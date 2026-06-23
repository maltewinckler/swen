"""Command to create or update local FinTS configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen.infrastructure.banking.local_fints.models.config import UpdateConfigResult
from swen.infrastructure.banking.local_fints.services.configuration_service import (
    FinTSConfigurationService,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateLocalFinTSConfigCommand:
    """Create or update the local FinTS configuration.

    Both `product_id` and `csv_content` are optional; at least one must be
    supplied.  On first-time setup both are required.  When only one is provided
    on an existing configuration only that field is patched.

    When `csv_content` is provided the `bank_information` and
    `fints_endpoints` lookup tables are repopulated via the service dependency.
    """

    def __init__(
        self,
        config_service: FinTSConfigurationService,
        admin_user_id: UUID,
    ):
        self._service = config_service
        self._admin_user_id = admin_user_id

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateLocalFinTSConfigCommand:
        """Create command from repository factory."""
        return cls(
            config_service=FinTSConfigurationService(
                config_repository=factory.fints_config_repository(),
                bank_info_repo=factory.bank_info_repository(),
                fints_endpoint_repo=factory.fints_endpoint_repository(),
            ),
            admin_user_id=factory.current_user.user_id,
        )

    async def execute(
        self,
        product_id: str | None = None,
        csv_content: bytes | None = None,
    ) -> UpdateConfigResult:
        """Upsert configuration and repopulate bank tables if CSV was provided."""
        return await self._service.update_configuration(
            admin_user_id=self._admin_user_id,
            product_id=product_id,
            csv_content=csv_content,
        )
