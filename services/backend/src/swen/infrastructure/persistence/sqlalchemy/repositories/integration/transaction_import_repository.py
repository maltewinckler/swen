"""SQLAlchemy implementation of TransactionImportRepository."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.banking.value_objects import BankTransaction
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
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction
    from swen.domain.accounting.entities import Account
    from swen.domain.shared.current_user import CurrentUser

logger = logging.getLogger(__name__)


class TransactionImportRepositorySQLAlchemy(TransactionImportRepository):
    """SQLAlchemy implementation of TransactionImportRepository."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: CurrentUser,
        transaction_repository: Optional[TransactionRepositorySQLAlchemy] = None,
    ):
        self._session = session
        self._user_id = current_user.user_id
        self._current_user = current_user
        self._transaction_repo = transaction_repository

    async def save(self, transaction_import: TransactionImport):
        await self._save_no_commit(transaction_import)
        await self._session.commit()

    async def _save_no_commit(self, transaction_import: TransactionImport) -> None:
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
            existing.booking_date = transaction_import.booking_date
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
                booking_date=transaction_import.booking_date,
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

    async def find_latest_booking_date_by_iban(self, iban: str) -> Optional[date]:
        stmt = (
            select(func.max(TransactionImportModel.booking_date))
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
                TransactionImportModel.status == ImportStatus.SUCCESS,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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
        await self._session.commit()
        return True

    def _model_to_domain(self, model: TransactionImportModel) -> TransactionImport:
        return TransactionImport.reconstitute(
            id=model.id,
            user_id=model.user_id,
            bank_transaction_id=model.bank_transaction_id,
            booking_date=model.booking_date,
            status=model.status,
            accounting_transaction_id=model.accounting_transaction_id,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
            imported_at=model.imported_at,
        )

    async def save_complete_import(
        self,
        import_record: TransactionImport,
        accounting_tx: Transaction,
        ob_adjustment: Optional[Transaction] = None,
    ) -> None:
        self._assert_user_owned(import_record, accounting_tx, ob_adjustment)
        transaction_repo = self._get_transaction_repository()

        async with self._atomic_scope():
            await transaction_repo._save_no_commit(accounting_tx)
            await self._save_no_commit(import_record)
            if ob_adjustment is not None:
                await transaction_repo._save_no_commit(ob_adjustment)

        if self._session.in_transaction():
            await self._session.commit()

    async def mark_reconciled_as_internal_transfer(
        self,
        import_record: TransactionImport,
        existing_transaction: Transaction,
        new_asset_account: Account,
        source_iban: str,
        counterparty_iban: str,
    ) -> None:
        self._assert_user_owned(import_record, existing_transaction)
        transaction_repo = self._get_transaction_repository()

        transfer_hash = BankTransaction.compute_transfer_hash(
            iban_a=source_iban,
            iban_b=counterparty_iban,
            booking_date=existing_transaction.date.date(),
            amount=existing_transaction.total_amount().amount,
        )

        converted = existing_transaction.convert_to_internal_transfer(
            new_asset_account=new_asset_account,
            transfer_hash=transfer_hash,
        )
        if not converted:
            msg = (
                f"Cannot convert transaction {existing_transaction.id} to internal "
                "transfer: no Income/Expense entry found"
            )
            raise ValueError(msg)

        import_record.mark_as_imported(existing_transaction.id)

        async with self._atomic_scope():
            await transaction_repo._save_no_commit(existing_transaction)
            await self._save_no_commit(import_record)

        if self._session.in_transaction():
            await self._session.commit()

    def _get_transaction_repository(self) -> TransactionRepositorySQLAlchemy:
        if self._transaction_repo is None:
            account_repo = AccountRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
            self._transaction_repo = TransactionRepositorySQLAlchemy(
                self._session,
                account_repo,
                self._current_user,
            )
        return self._transaction_repo

    def _atomic_scope(self):
        """Open a savepoint or top-level transaction.

        Uses a savepoint when an outer transaction is already active and a new
        top-level transaction otherwise. Either way, the wrapped writes are
        all-or-nothing relative to a failure inside the block.
        """
        if self._session.in_transaction():
            return self._session.begin_nested()
        return self._session.begin()

    def _assert_user_owned(
        self,
        import_record: TransactionImport,
        accounting_tx: Transaction,
        ob_adjustment: Optional[Transaction] = None,
    ) -> None:
        if import_record.user_id != self._user_id:
            msg = (
                f"Import record {import_record.id} belongs to user "
                f"{import_record.user_id}, not {self._user_id}"
            )
            raise PermissionError(msg)
        if accounting_tx.user_id != self._user_id:
            msg = (
                f"Accounting transaction {accounting_tx.id} belongs to user "
                f"{accounting_tx.user_id}, not {self._user_id}"
            )
            raise PermissionError(msg)
        if ob_adjustment is not None and ob_adjustment.user_id != self._user_id:
            msg = (
                f"Opening-balance adjustment {ob_adjustment.id} belongs to user "
                f"{ob_adjustment.user_id}, not {self._user_id}"
            )
            raise PermissionError(msg)
