"""SQLAlchemy implementation of AccountMappingRepository.

This implementation is user-scoped via CurrentUser, meaning all queries
automatically filter by the current user's user_id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.repositories import AccountMappingRepository
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    AccountMappingModel,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser


class AccountMappingRepositorySQLAlchemy(AccountMappingRepository):
    """SQLAlchemy implementation of AccountMappingRepository."""

    def __init__(self, session: AsyncSession, current_user: CurrentUser):
        self._session = session
        self._user_id = current_user.user_id

    async def save(self, mapping: AccountMapping) -> None:
        # Check if mapping exists
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.id == mapping.id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing mapping
            existing.user_id = mapping.user_id
            existing.iban = mapping.iban
            existing.accounting_account_id = mapping.accounting_account_id
            existing.account_name = mapping.account_name
            existing.is_active = mapping.is_active
            existing.updated_at = mapping.updated_at
        else:
            # Create new mapping
            model = AccountMappingModel(
                id=mapping.id,
                user_id=mapping.user_id,
                iban=mapping.iban,
                accounting_account_id=mapping.accounting_account_id,
                account_name=mapping.account_name,
                is_active=mapping.is_active,
                created_at=mapping.created_at,
                updated_at=mapping.updated_at,
            )
            self._session.add(model)

        await self._session.flush()

    async def find_by_id(self, mapping_id: UUID) -> Optional[AccountMapping]:
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.id == mapping_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_by_iban(self, iban: str) -> Optional[AccountMapping]:
        normalized_iban = iban.strip().upper()
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.iban == normalized_iban,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_by_accounting_account_id(
        self,
        account_id: UUID,
    ) -> List[AccountMapping]:
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.accounting_account_id == account_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_all_active(self) -> List[AccountMapping]:
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.is_active == True,  # NOQA: E712
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_all(self) -> List[AccountMapping]:
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def delete(self, mapping_id: UUID) -> bool:
        stmt = select(AccountMappingModel).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.id == mapping_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def exists_for_iban(self, iban: str) -> bool:
        normalized_iban = iban.strip().upper()
        stmt = select(AccountMappingModel.id).where(
            AccountMappingModel.user_id == self._user_id,
            AccountMappingModel.iban == normalized_iban,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _model_to_domain(self, model: AccountMappingModel) -> AccountMapping:
        # Reconstruct the entity
        mapping = AccountMapping.__new__(AccountMapping)
        mapping._id = model.id
        mapping._user_id = model.user_id
        mapping._iban = model.iban
        mapping._accounting_account_id = model.accounting_account_id
        mapping._account_name = model.account_name
        mapping._is_active = model.is_active
        mapping._created_at = model.created_at
        mapping._updated_at = model.updated_at

        return mapping
