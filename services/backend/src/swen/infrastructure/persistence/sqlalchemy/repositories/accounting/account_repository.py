"""SQLAlchemy implementation of AccountRepository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountAlreadyExistsError
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.value_objects import Currency
from swen.domain.shared.iban import normalize_iban
from swen.infrastructure.persistence.sqlalchemy.models import AccountModel

if TYPE_CHECKING:
    from swen.application.context import UserContext

logger = logging.getLogger(__name__)


class AccountRepositorySQLAlchemy(AccountRepository):
    """SQLAlchemy implementation of accounting account repository."""

    def __init__(self, session: AsyncSession, user_context: UserContext):
        self._session = session
        self._user_id = user_context.user_id

    async def save(self, account: Account) -> None:
        # Check if account already exists
        model = await self._find_model_by_id(account.id)

        if model:
            # Update existing
            logger.debug("Updating existing account: %s", account.name)
            self._update_model_from_domain(model, account)
        else:
            # Create new
            logger.debug("Creating new account: %s", account.name)
            model = self._create_model_from_domain(account)
            self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Keep session usable after a failed flush
            await self._session.rollback()

            msg = str(getattr(exc, "orig", exc))
            # Check for duplicate account_number (supports SQLite and PostgreSQL)
            if (
                "accounting_accounts.user_id, accounting_accounts.account_number" in msg
                or "uq_accounts_user_account_number" in msg
            ):
                raise AccountAlreadyExistsError(
                    account_number=account.account_number,
                    message=f"Account number '{account.account_number}' already exists",
                ) from exc

            # Check for duplicate IBAN (supports SQLite and PostgreSQL)
            if (
                "accounting_accounts.user_id, accounting_accounts.iban" in msg
                or "uq_accounts_user_iban" in msg
            ):
                raise AccountAlreadyExistsError(
                    account_number=account.iban,
                    message=f"IBAN '{account.iban}' is already mapped to an account",
                ) from exc

            error_msg = f"Failed to save account due to database constraint: {msg}"
            raise ValueError(error_msg) from exc

        logger.info("Account saved: %s (ID: %s)", account.name, account.id)

    async def find_by_id(self, account_id: UUID) -> Optional[Account]:
        model = await self._find_model_by_id(account_id)

        if not model:
            return None

        return self._map_to_domain(model)

    async def find_by_name(self, name: str) -> Optional[Account]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.name == name,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._map_to_domain(model)

    async def find_by_account_number(self, account_number: str) -> Optional[Account]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.account_number == account_number,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._map_to_domain(model)

    async def find_by_iban(self, iban: str) -> Optional[Account]:
        normalized = normalize_iban(iban)
        if not normalized:
            return None

        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.iban == normalized,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._map_to_domain(model) if model else None

    async def find_all_active(self) -> list[Account]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.is_active == True,  # NOQA: E712
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def find_all(self) -> list[Account]:
        stmt = select(AccountModel).where(AccountModel.user_id == self._user_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def find_by_type(self, account_type: str) -> list[Account]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.account_type == account_type,
            AccountModel.is_active == True,  # NOQA: E712
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def delete(self, account_id: UUID) -> None:
        model = await self._find_model_by_id(account_id)

        if model:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("Account deleted: %s", account_id)

    async def find_children(self, parent_id: UUID) -> list[Account]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.parent_id == parent_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._map_to_domain(model) for model in models]

    async def find_descendants(self, parent_id: UUID) -> list[Account]:
        descendants: list[Account] = []
        to_process = [parent_id]
        seen: set[UUID] = set()

        while to_process:
            current_id = to_process.pop()
            if current_id in seen:
                continue
            seen.add(current_id)

            children = await self.find_children(current_id)
            descendants.extend(children)
            to_process.extend([c.id for c in children])

        return descendants

    async def has_children(self, account_id: UUID) -> bool:
        stmt = (
            select(AccountModel.id)
            .where(
                AccountModel.user_id == self._user_id,
                AccountModel.parent_id == account_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def is_parent(self, account_id: UUID) -> bool:
        return await self.has_children(account_id)

    async def find_by_parent_id(self, parent_id: UUID) -> list[Account]:
        return await self.find_children(parent_id)

    async def get_hierarchy_path(self, account_id: UUID) -> list[Account]:
        path = []
        current_id: Optional[UUID] = account_id

        while current_id:
            account = await self.find_by_id(current_id)
            if not account:
                break
            path.insert(0, account)  # Prepend
            current_id = account.parent_id

        return path

    async def _find_model_by_id(self, account_id: UUID) -> Optional[AccountModel]:
        stmt = select(AccountModel).where(
            AccountModel.user_id == self._user_id,
            AccountModel.id == account_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _create_model_from_domain(self, account: Account) -> AccountModel:
        return AccountModel(
            id=account.id,
            user_id=account.user_id,
            name=account.name,
            account_type=account.account_type.value,
            account_number=account.account_number,
            iban=account.iban,
            description=account.description,
            default_currency=account.default_currency.code,
            is_active=account.is_active,
            parent_id=account.parent_id,
            created_at=account.created_at,
        )

    def _update_model_from_domain(
        self,
        model: AccountModel,
        account: Account,
    ) -> None:
        model.user_id = account.user_id
        model.name = account.name
        model.account_type = account.account_type.value
        model.account_number = account.account_number
        model.iban = account.iban
        model.description = account.description
        model.default_currency = account.default_currency.code
        model.is_active = account.is_active
        model.parent_id = account.parent_id

    def _map_to_domain(self, model: AccountModel) -> Account:
        return Account.reconstitute(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            account_type=AccountType(model.account_type),
            account_number=model.account_number or "",
            default_currency=Currency(model.default_currency),
            is_active=model.is_active,
            created_at=model.created_at,
            iban=model.iban,
            description=model.description,
            parent_id=model.parent_id,
        )
