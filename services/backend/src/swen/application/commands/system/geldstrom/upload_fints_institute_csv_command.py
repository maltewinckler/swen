"""Command to upload FinTS institute CSV."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.banking.value_objects.bank_info import BankInfo
from swen.infrastructure.banking.geldstrom.fints_config import UploadResult
from swen.infrastructure.banking.geldstrom.fints_institute_directory import (
    FinTSInstituteDirectory,
)
from swen.infrastructure.system.geldstrom.fints_configuration_service import (
    FinTSConfigurationService,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.repositories.bank_info_repository import (
        BankInfoRepository,
    )
    from swen.infrastructure.banking.geldstrom.fints_endpoint_repository import (
        FinTSEndpointRepository,
    )

logger = logging.getLogger(__name__)


class UploadFinTSInstituteCSVCommand:
    """Upload and process FinTS institute CSV file."""

    def __init__(
        self,
        config_service: FinTSConfigurationService,
        admin_user_id: UUID,
        bank_info_repo: BankInfoRepository,
        fints_endpoint_repo: FinTSEndpointRepository,
    ):
        self._service = config_service
        self._admin_user_id = admin_user_id
        self._bank_info_repo = bank_info_repo
        self._fints_endpoint_repo = fints_endpoint_repo

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
            bank_info_repo=factory.bank_info_repository(),
            fints_endpoint_repo=factory.fints_endpoint_repository(),
        )

    async def execute(self, csv_content: bytes) -> UploadResult:
        """Upload CSV, then populate bank_information and fints_endpoints."""
        result = await self._service.upload_csv(
            csv_content=csv_content,
            admin_user_id=self._admin_user_id,
        )

        # Populate the lookup tables from the parsed CSV
        await self._populate_tables(csv_content)

        logger.info(
            "CSV uploaded by admin %s: %d institutes parsed",
            self._admin_user_id,
            result.institute_count,
        )

        return result

    async def _populate_tables(self, csv_content: bytes) -> None:
        """Parse CSV and upsert bank_information + fints_endpoints tables."""
        directory = FinTSInstituteDirectory()
        if not directory.load_from_bytes(csv_content):
            logger.warning("Failed to parse CSV for table population")
            return

        banks: list[BankInfo] = []
        endpoints: dict[str, str] = {}

        for blz, info in directory._blz_index.items():
            banks.append(
                BankInfo(
                    blz=blz,
                    name=info.name,
                    bic=info.bic or None,
                    organization=None,
                    is_fints_capable=True,
                ),
            )
            endpoints[blz] = info.endpoint_url

        bank_count = await self._bank_info_repo.save_batch(banks, source="csv")
        endpoint_count = await self._fints_endpoint_repo.save_batch(endpoints)

        logger.info(
            "Populated bank tables: %d bank_information, %d fints_endpoints",
            bank_count,
            endpoint_count,
        )
