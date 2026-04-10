"""Command to save Geldstrom API configuration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

import httpx

from swen.infrastructure.banking.geldstrom_api.config import (
    GeldstromApiConfig,
)
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT = 10.0


class GeldstromApiVerificationError(Exception):
    """Raised when the Geldstrom API health check fails."""


class SaveGeldstromApiConfigCommand:
    """Save Geldstrom API configuration with endpoint verification."""

    def __init__(
        self,
        config_repository: GeldstromApiConfigRepository,
        admin_user_id: UUID,
    ):
        self._repository = config_repository
        self._admin_user_id = admin_user_id

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> SaveGeldstromApiConfigCommand:
        return cls(
            config_repository=factory.geldstrom_api_config_repository(),
            admin_user_id=factory.current_user.user_id,
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
