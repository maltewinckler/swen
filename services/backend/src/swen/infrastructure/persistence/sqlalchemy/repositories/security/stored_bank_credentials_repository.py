"""SQLAlchemy implementation of StoredBankCredentialsRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.security.entities import StoredBankCredentials
from swen.domain.security.exceptions import CredentialNotFoundError
from swen.domain.security.repositories import StoredBankCredentialsRepository
from swen.infrastructure.persistence.sqlalchemy.models import (
    StoredCredentialModel,
)

if TYPE_CHECKING:
    from swen.application.context import UserContext


class StoredBankCredentialsRepositorySQLAlchemy(StoredBankCredentialsRepository):
    """SQLAlchemy implementation for encrypted credential storage."""

    def __init__(self, session: AsyncSession, user_context: UserContext):
        self._session = session
        self._user_id = user_context.user_id

    async def save(
        self,
        stored_credentials: StoredBankCredentials,
    ) -> None:
        existing = await self._find_model_by_blz(stored_credentials.blz)
        if existing:
            msg = (
                f"Credentials already exist for user {self._user_id}, "
                f"BLZ {stored_credentials.blz}"
            )
            raise ValueError(msg)

        # Create database model from entity
        model = self._entity_to_model(stored_credentials)

        self._session.add(model)
        await self._session.flush()

    async def find_by_blz(self, blz: str) -> Optional[StoredBankCredentials]:
        model = await self._find_model_by_blz(blz)

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_by_id(self, credential_id: str) -> Optional[StoredBankCredentials]:
        stmt = select(StoredCredentialModel).where(
            StoredCredentialModel.user_id == self._user_id,
            StoredCredentialModel.id == credential_id,
            StoredCredentialModel.is_active == True,  # noqa: E712
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_entity(model)

    async def find_all(self) -> list[StoredBankCredentials]:
        stmt = (
            select(StoredCredentialModel)
            .where(
                StoredCredentialModel.user_id == self._user_id,
                StoredCredentialModel.is_active == True,  # noqa: E712
            )
            .order_by(StoredCredentialModel.created_at)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def delete(self, blz: str) -> bool:
        model = await self._find_model_by_blz(blz)

        if not model:
            return False

        # Soft delete
        model.is_active = False
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

        return True

    async def update_last_used(self, blz: str) -> None:
        model = await self._find_model_by_blz(blz)

        if not model:
            msg = f"Credentials not found for user {self._user_id}, BLZ {blz}"
            raise CredentialNotFoundError(msg)

        model.last_used_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    # Private helpers

    async def _find_model_by_blz(
        self,
        blz: str,
    ) -> Optional[StoredCredentialModel]:
        stmt = select(StoredCredentialModel).where(
            StoredCredentialModel.user_id == self._user_id,
            StoredCredentialModel.blz == blz,
            StoredCredentialModel.is_active == True,  # noqa: E712
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _model_to_entity(model: StoredCredentialModel) -> StoredBankCredentials:
        return StoredBankCredentials(
            id=model.id,
            user_id=model.user_id,
            blz=model.blz,
            endpoint=model.endpoint,
            username_encrypted=model.username_encrypted,
            pin_encrypted=model.pin_encrypted,
            encryption_version=model.encryption_version,
            label=model.label,
            is_active=model.is_active,
            tan_method=model.tan_method,
            tan_medium=model.tan_medium,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_used_at=model.last_used_at,
        )

    @staticmethod
    def _entity_to_model(entity: StoredBankCredentials) -> StoredCredentialModel:
        return StoredCredentialModel(
            id=entity.id,
            user_id=entity.user_id,
            blz=entity.blz,
            endpoint=entity.endpoint,
            username_encrypted=entity.username_encrypted,
            pin_encrypted=entity.pin_encrypted,
            encryption_version=entity.encryption_version,
            label=entity.label,
            is_active=entity.is_active,
            tan_method=entity.tan_method,
            tan_medium=entity.tan_medium,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_used_at=entity.last_used_at,
        )
