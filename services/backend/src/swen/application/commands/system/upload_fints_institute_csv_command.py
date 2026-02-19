"""Command to upload FinTS institute CSV."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.infrastructure.banking.fints_config import UploadResult
from swen.infrastructure.system.fints_configuration_service import (
    FinTSConfigurationService,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory

logger = logging.getLogger(__name__)


class UploadFinTSInstituteCSVCommand:
    """Upload and process FinTS institute CSV file."""

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
    ) -> UploadFinTSInstituteCSVCommand:
        """Create command from repository factory."""
        return cls(
            config_service=FinTSConfigurationService(
                repository=factory.fints_config_repository(),
            ),
            admin_user_id=factory.current_user.user_id,
        )

    async def execute(self, csv_content: bytes) -> UploadResult:
        """Upload CSV with validation."""
        result = await self._service.upload_csv(
            csv_content=csv_content,
            admin_user_id=self._admin_user_id,
        )

        logger.info(
            "CSV uploaded by admin %s: %d institutes parsed",
            self._admin_user_id,
            result.institute_count,
        )

        return result
