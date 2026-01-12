"""SQLAlchemy implementation of TransactionImportRepository."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.repositories import TransactionImportRepository
from swen.domain.integration.value_objects import ImportStatus
from swen.infrastructure.persistence.sqlalchemy.models.banking import (
    BankAccountModel,
    BankTransactionModel,
)
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    TransactionImportModel,
)

if TYPE_CHECKING:
    from swen.application.context import UserContext


class TransactionImportRepositorySQLAlchemy(TransactionImportRepository):
    """SQLAlchemy implementation of TransactionImportRepository."""

    def __init__(self, session: AsyncSession, user_context: UserContext):
        self._session = session
        self._user_id = user_context.user_id

    async def save(self, transaction_import: TransactionImport):
        # Check if import exists
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.id == transaction_import.id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing import
            existing.user_id = transaction_import.user_id
            existing.bank_transaction_id = transaction_import.bank_transaction_id
            existing.status = transaction_import.status
            existing.accounting_transaction_id = (
                transaction_import.accounting_transaction_id
            )
            existing.error_message = transaction_import.error_message
            existing.updated_at = transaction_import.updated_at
            existing.imported_at = transaction_import.imported_at
        else:
            # Create new import
            model = TransactionImportModel(
                id=transaction_import.id,
                user_id=transaction_import.user_id,
                bank_transaction_id=transaction_import.bank_transaction_id,
                status=transaction_import.status,
                accounting_transaction_id=transaction_import.accounting_transaction_id,
                error_message=transaction_import.error_message,
                created_at=transaction_import.created_at,
                updated_at=transaction_import.updated_at,
                imported_at=transaction_import.imported_at,
            )
            self._session.add(model)

        await self._session.flush()

    async def find_by_id(self, import_id: UUID) -> Optional[TransactionImport]:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.id == import_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_by_bank_transaction_id(
        self,
        bank_transaction_id: UUID,
    ) -> Optional[TransactionImport]:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.bank_transaction_id == bank_transaction_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_by_accounting_transaction_id(
        self,
        transaction_id: UUID,
    ) -> Optional[TransactionImport]:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.accounting_transaction_id == transaction_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_by_status(self, status: ImportStatus) -> List[TransactionImport]:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.status == status,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_iban(self, iban: str) -> List[TransactionImport]:
        stmt = (
            select(TransactionImportModel)
            .join(
                BankTransactionModel,
                TransactionImportModel.bank_transaction_id == BankTransactionModel.id,
            )
            .join(
                BankAccountModel,
                BankTransactionModel.account_id == BankAccountModel.id,
            )
            .where(
                TransactionImportModel.user_id == self._user_id,
                BankAccountModel.iban == iban,
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_failed_imports(
        self,
        since: Optional[datetime] = None,
    ) -> List[TransactionImport]:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.status == ImportStatus.FAILED,
        )

        if since:
            stmt = stmt.where(TransactionImportModel.created_at >= since)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_imports_in_date_range(
        self,
        iban: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[TransactionImport]:
        stmt = (
            select(TransactionImportModel)
            .join(
                BankTransactionModel,
                TransactionImportModel.bank_transaction_id == BankTransactionModel.id,
            )
            .join(
                BankAccountModel,
                BankTransactionModel.account_id == BankAccountModel.id,
            )
            .where(
                TransactionImportModel.user_id == self._user_id,
                BankAccountModel.iban == iban,
                TransactionImportModel.created_at >= start_date,
                TransactionImportModel.created_at <= end_date,
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def count_by_status(self, iban: Optional[str] = None) -> dict[str, int]:
        if iban:
            stmt = (
                select(
                    TransactionImportModel.status,
                    func.count(TransactionImportModel.id),
                )
                .join(
                    BankTransactionModel,
                    TransactionImportModel.bank_transaction_id
                    == BankTransactionModel.id,
                )
                .join(
                    BankAccountModel,
                    BankTransactionModel.account_id == BankAccountModel.id,
                )
                .where(
                    TransactionImportModel.user_id == self._user_id,
                    BankAccountModel.iban == iban,
                )
                .group_by(TransactionImportModel.status)
            )
        else:
            stmt = (
                select(
                    TransactionImportModel.status,
                    func.count(TransactionImportModel.id),
                )
                .where(TransactionImportModel.user_id == self._user_id)
                .group_by(TransactionImportModel.status)
            )

        result = await self._session.execute(stmt)
        rows = result.all()

        return {status.value: count for status, count in rows}

    async def delete(self, import_id: UUID) -> bool:
        stmt = select(TransactionImportModel).where(
            TransactionImportModel.user_id == self._user_id,
            TransactionImportModel.id == import_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    def _model_to_domain(self, model: TransactionImportModel) -> TransactionImport:
        return TransactionImport.reconstitute(
            id=model.id,
            user_id=model.user_id,
            bank_transaction_id=model.bank_transaction_id,
            status=model.status,
            accounting_transaction_id=model.accounting_transaction_id,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
            imported_at=model.imported_at,
        )
