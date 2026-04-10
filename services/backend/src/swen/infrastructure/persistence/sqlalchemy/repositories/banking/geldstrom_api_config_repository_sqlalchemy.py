"""SQLAlchemy implementation of Geldstrom API configuration repository."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.security.services import EncryptionService
from swen.infrastructure.banking.geldstrom_api.config import GeldstromApiConfig
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)
from swen.infrastructure.persistence.sqlalchemy.models.banking.geldstrom_api_config_model import (  # NOQA: E501
    GeldstromApiConfigModel,
)

logger = logging.getLogger(__name__)


class GeldstromApiConfigRepositorySQLAlchemy(GeldstromApiConfigRepository):
    """SQLAlchemy implementation of Geldstrom API configuration repository.

    Handles encryption/decryption of API key at the persistence
    boundary, singleton pattern enforcement (id=1), and audit tracking.
    """

    def __init__(
        self,
        session: AsyncSession,
        encryption_service: EncryptionService,
    ):
        self._session = session
        self._encryption = encryption_service

    async def get_configuration(self) -> GeldstromApiConfig | None:
        """Get current configuration with decrypted API key."""
        stmt = select(GeldstromApiConfigModel).where(
            GeldstromApiConfigModel.id == 1,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        api_key = self._encryption.decrypt(model.api_key_encrypted)

        return GeldstromApiConfig(
            api_key=api_key,
            endpoint_url=model.endpoint_url,
            is_active=model.is_active,
            created_at=model.created_at,
            created_by_id=str(model.created_by),
            updated_at=model.updated_at,
            updated_by_id=str(model.updated_by),
        )

    async def save_configuration(
        self,
        config: GeldstromApiConfig,
        admin_user_id: UUID,
    ) -> None:
        """Save or update complete configuration."""
        now = datetime.now(timezone.utc)
        api_key_encrypted = self._encryption.encrypt(config.api_key)

        existing = await self._session.get(GeldstromApiConfigModel, 1)

        if existing:
            existing.api_key_encrypted = api_key_encrypted
            existing.endpoint_url = config.endpoint_url
            existing.is_active = config.is_active
            existing.updated_at = now
            existing.updated_by = admin_user_id
        else:
            model = GeldstromApiConfigModel(
                id=1,
                api_key_encrypted=api_key_encrypted,
                endpoint_url=config.endpoint_url,
                is_active=config.is_active,
                created_by=admin_user_id,
                updated_by=admin_user_id,
            )
            self._session.add(model)

        await self._session.flush()

    async def exists(self) -> bool:
        """Check if configuration exists."""
        stmt = select(GeldstromApiConfigModel.id).where(
            GeldstromApiConfigModel.id == 1,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def activate(self, admin_user_id: UUID) -> None:
        """Set is_active=True."""
        existing = await self._session.get(GeldstromApiConfigModel, 1)
        if not existing:
            msg = "Cannot activate: Geldstrom API configuration does not exist"
            raise ValueError(msg)
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        existing.updated_by = admin_user_id
        await self._session.flush()

    async def deactivate(self, admin_user_id: UUID) -> None:
        """Set is_active=False."""
        existing = await self._session.get(GeldstromApiConfigModel, 1)
        if not existing:
            return  # Nothing to deactivate
        existing.is_active = False
        existing.updated_at = datetime.now(timezone.utc)
        existing.updated_by = admin_user_id
        await self._session.flush()

    async def is_active(self) -> bool:
        """Check if configuration exists and is active."""
        stmt = select(GeldstromApiConfigModel.is_active).where(
            GeldstromApiConfigModel.id == 1,
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return value is True
