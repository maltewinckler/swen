"""Command to save Geldstrom API configuration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

import httpx

from swen.domain.banking.value_objects.bank_info import BankInfo
from swen.infrastructure.banking.geldstrom_api.config import (
    GeldstromApiConfig,
)
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.repositories.bank_info_repository import (
        BankInfoRepository,
    )

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT = 10.0
_LOOKUP_TIMEOUT = 30.0


class GeldstromApiVerificationError(Exception):
    """Raised when the Geldstrom API health check fails."""


class SaveGeldstromApiConfigCommand:
    """Save Geldstrom API configuration with endpoint verification."""

    def __init__(
        self,
        config_repository: GeldstromApiConfigRepository,
        admin_user_id: UUID,
        bank_info_repo: BankInfoRepository,
    ):
        self._repository = config_repository
        self._admin_user_id = admin_user_id
        self._bank_info_repo = bank_info_repo

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> SaveGeldstromApiConfigCommand:
        return cls(
            config_repository=factory.geldstrom_api_config_repository(),
            admin_user_id=factory.current_user.user_id,
            bank_info_repo=factory.bank_info_repository(),
        )

    async def execute(
        self,
        api_key: str,
        endpoint_url: str,
    ) -> None:
        """Save API config after verifying the endpoint is reachable."""
        endpoint_url = endpoint_url.rstrip("/")

        await self._verify_endpoint(endpoint_url, api_key)

        config = GeldstromApiConfig(
            api_key=api_key,
            endpoint_url=endpoint_url,
            is_active=False,
            updated_by_id=str(self._admin_user_id),
        )
        await self._repository.save_configuration(
            config,
            admin_user_id=self._admin_user_id,
        )

        logger.info(
            "Geldstrom API config saved by admin %s",
            self._admin_user_id,
        )

        # Populate bank_information table from API bank directory
        await self._populate_bank_info(endpoint_url, api_key)

    async def _populate_bank_info(
        self,
        endpoint_url: str,
        api_key: str,
    ) -> None:
        """Fetch bank directory from Geldstrom API and populate bank_information."""
        try:
            async with httpx.AsyncClient(timeout=_LOOKUP_TIMEOUT) as client:
                response = await client.get(
                    f"{endpoint_url}/v1/banking/lookup",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()

            entries = response.json()
            if not isinstance(entries, list):
                logger.warning("Unexpected lookup response format")
                return

            banks = [
                BankInfo(
                    blz=entry["blz"],
                    name=entry.get("name", ""),
                    bic=entry.get("bic"),
                    organization=entry.get("organization"),
                    is_fints_capable=entry.get("is_fints_capable", True),
                )
                for entry in entries
                if "blz" in entry and entry.get("name")
            ]

            if banks:
                count = await self._bank_info_repo.save_batch(banks, source="api")
                logger.info("Populated %d banks from Geldstrom API", count)

        except Exception:
            logger.exception("Failed to populate bank info from Geldstrom API")

    @staticmethod
    async def _verify_endpoint(
        endpoint_url: str,
        api_key: str,
    ) -> None:
        """Verify the Geldstrom API endpoint is reachable."""
        health_url = f"{endpoint_url}/health/ready"
        try:
            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
                response = await client.get(
                    health_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
        except httpx.ConnectError as e:
            msg = f"Cannot connect to {endpoint_url}: {e}"
            raise GeldstromApiVerificationError(msg) from e
        except httpx.TimeoutException as e:
            msg = f"Timeout connecting to {endpoint_url}"
            raise GeldstromApiVerificationError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"Health check failed (HTTP {e.response.status_code})"
            raise GeldstromApiVerificationError(msg) from e
