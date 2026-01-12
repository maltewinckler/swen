"""SQLAlchemy implementation of BankAccountRepository."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.banking.repositories import BankAccountRepository
from swen.domain.banking.value_objects import BankAccount
from swen.infrastructure.persistence.sqlalchemy.models import BankAccountModel

if TYPE_CHECKING:
    from swen.application.context import UserContext

logger = logging.getLogger(__name__)


class BankAccountRepositorySQLAlchemy(BankAccountRepository):
    """SQLAlchemy implementation of bank account repository."""

    def __init__(self, session: AsyncSession, user_context: UserContext):
        self._session = session
        self._user_id = user_context.user_id

    async def save(self, bank_account: BankAccount):
        model = await self._find_model_by_iban(bank_account.iban)

        if model:
            # Update existing
            logger.debug("Updating existing bank account: %s", bank_account.iban)
            self._update_model_from_domain(model, bank_account)
        else:
            # Create new
            logger.debug("Creating new bank account: %s", bank_account.iban)
            model = self._create_model_from_domain(bank_account)
            self._session.add(model)

        await self._session.flush()
        logger.info("Bank account saved: %s", bank_account.iban)

    async def find_by_iban(self, iban: str) -> Optional[BankAccount]:
        model = await self._find_model_by_iban(iban)

        if not model:
            return None

        return self._map_to_domain(model)

    async def find_all(self) -> list[BankAccount]:
        stmt = select(BankAccountModel).where(
            BankAccountModel.user_id == self._user_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def find_by_blz(self, blz: str) -> list[BankAccount]:
        stmt = select(BankAccountModel).where(
            BankAccountModel.user_id == self._user_id,
            BankAccountModel.blz == blz,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def delete(self, iban: str) -> None:
        model = await self._find_model_by_iban(iban)

        if model:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("Bank account deleted: %s", iban)

    async def update_last_sync(self, iban: str, sync_time: datetime) -> None:
        model = await self._find_model_by_iban(iban)

        if model:
            model.last_sync_at = sync_time
            await self._session.flush()
            logger.debug("Updated last sync for account: %s", iban)

    async def _find_model_by_iban(self, iban: str) -> Optional[BankAccountModel]:
        stmt = select(BankAccountModel).where(
            BankAccountModel.iban == iban,
            BankAccountModel.user_id == self._user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _create_model_from_domain(self, bank_account: BankAccount) -> BankAccountModel:
        return BankAccountModel(
            user_id=self._user_id,
            iban=bank_account.iban,
            account_number=bank_account.account_number,
            blz=bank_account.blz,
            bic=bank_account.bic,
            owner_name=bank_account.account_holder,  # Map: account_holder → owner_name
            bank_name=bank_account.bank_name,
            account_type=bank_account.account_type,
            currency=bank_account.currency,
            balance=bank_account.balance,
            balance_date=bank_account.balance_date,
        )

    def _update_model_from_domain(
        self,
        model: BankAccountModel,
        bank_account: BankAccount,
    ) -> None:
        model.account_number = bank_account.account_number
        model.blz = bank_account.blz
        model.bic = bank_account.bic
        model.owner_name = bank_account.account_holder
        model.bank_name = bank_account.bank_name
        model.account_type = bank_account.account_type
        model.currency = bank_account.currency
        model.balance = bank_account.balance
        model.balance_date = bank_account.balance_date

    def _map_to_domain(self, model: BankAccountModel) -> BankAccount:
        return BankAccount(
            iban=model.iban,
            account_number=model.account_number or "",
            blz=model.blz,
            account_holder=model.owner_name,  # Map: owner_name → account_holder
            account_type=model.account_type or "Girokonto",
            currency=model.currency,
            bic=model.bic or "",
            balance=model.balance,
            balance_date=model.balance_date,
            bank_name=model.bank_name or "",
        )
