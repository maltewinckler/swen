"""SQLAlchemy implementation of FinTS configuration repository."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.security.services import EncryptionService
from swen.infrastructure.banking.fints_config import FinTSConfig
from swen.infrastructure.banking.fints_config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.persistence.sqlalchemy.models.banking.fints_config_model import (  # NOQA: E501
    FinTSConfigModel,
)

logger = logging.getLogger(__name__)


class FinTSConfigRepositorySQLAlchemy(FinTSConfigRepository):
    """SQLAlchemy implementation of FinTS configuration repository.

    Handles encryption/decryption of Product ID at the persistence
    boundary, singleton pattern enforcement (id=1), and audit tracking.
    """

    def __init__(
        self,
        session: AsyncSession,
        encryption_service: EncryptionService,
    ):
        self._session = session
        self._encryption = encryption_service

    async def get_configuration(self) -> FinTSConfig | None:
        """Get current FinTS configuration with decrypted Product ID."""
        stmt = select(FinTSConfigModel).where(FinTSConfigModel.id == 1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Decrypt Product ID
        product_id = self._encryption.decrypt(model.product_id_encrypted)

        return FinTSConfig(
            product_id=product_id,
            csv_content=model.csv_content,
            csv_encoding=model.csv_encoding,
            csv_upload_timestamp=model.csv_upload_timestamp,
            csv_file_size_bytes=model.csv_file_size_bytes,
            csv_institute_count=model.csv_institute_count,
            created_at=model.created_at,
            created_by_id=str(model.created_by),
            updated_at=model.updated_at,
            updated_by_id=str(model.updated_by),
        )

    async def save_configuration(
        self,
        config: FinTSConfig,
        admin_user_id: UUID,
    ) -> None:
        """Save or update complete configuration."""
        now = datetime.now(timezone.utc)
        product_id_encrypted = self._encryption.encrypt(config.product_id)

        # Check if exists
        existing = await self._session.get(FinTSConfigModel, 1)

        if existing:
            existing.product_id_encrypted = product_id_encrypted
            existing.csv_content = config.csv_content
            existing.csv_encoding = config.csv_encoding
            existing.csv_upload_timestamp = config.csv_upload_timestamp
            existing.csv_file_size_bytes = config.csv_file_size_bytes
            existing.csv_institute_count = config.csv_institute_count
            existing.updated_at = now
            existing.updated_by = admin_user_id
        else:
            model = FinTSConfigModel(
                id=1,
                product_id_encrypted=product_id_encrypted,
                csv_content=config.csv_content,
                csv_encoding=config.csv_encoding,
                csv_upload_timestamp=config.csv_upload_timestamp,
                csv_file_size_bytes=config.csv_file_size_bytes,
                csv_institute_count=config.csv_institute_count,
                created_by=admin_user_id,
                updated_by=admin_user_id,
            )
            self._session.add(model)

        await self._session.flush()

    async def update_product_id(
        self,
        product_id: str,
        admin_user_id: UUID,
    ) -> None:
        """Update only Product ID, keeping CSV unchanged."""
        existing = await self._session.get(FinTSConfigModel, 1)
        if not existing:
            msg = "Cannot update Product ID: configuration does not exist"
            raise ValueError(msg)

        existing.product_id_encrypted = self._encryption.encrypt(product_id)
        existing.updated_at = datetime.now(timezone.utc)
        existing.updated_by = admin_user_id

        await self._session.flush()

    async def update_csv(
        self,
        csv_content: bytes,
        encoding: str,
        institute_count: int,
        admin_user_id: UUID,
    ) -> None:
        """Update only CSV data, keeping Product ID unchanged."""
        now = datetime.now(timezone.utc)

        existing = await self._session.get(FinTSConfigModel, 1)
        if not existing:
            msg = "Cannot update CSV: configuration does not exist"
            raise ValueError(msg)

        existing.csv_content = csv_content
        existing.csv_encoding = encoding
        existing.csv_institute_count = institute_count
        existing.csv_upload_timestamp = now
        existing.csv_file_size_bytes = len(csv_content)
        existing.updated_at = now
        existing.updated_by = admin_user_id

        await self._session.flush()

    async def exists(self) -> bool:
        """Check if configuration exists."""
        stmt = select(FinTSConfigModel.id).where(FinTSConfigModel.id == 1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
