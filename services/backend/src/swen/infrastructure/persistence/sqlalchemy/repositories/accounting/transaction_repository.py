"""SQLAlchemy implementation of TransactionRepository.

This implementation is user-scoped via CurrentUser, meaning all queries
automatically filter by the current user's user_id.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import JournalEntry
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource
from swen.domain.shared.iban import normalize_iban
from swen.infrastructure.persistence.sqlalchemy.models import (
    JournalEntryModel,
    TransactionModel,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser

logger = logging.getLogger(__name__)


class TransactionRepositorySQLAlchemy(TransactionRepository):
    """SQLAlchemy implementation of accounting transaction repository."""

    def __init__(
        self,
        session: AsyncSession,
        account_repository: AccountRepository,
        current_user: CurrentUser,
    ):
        self._session = session
        self._account_repo = account_repository
        self._user_id = current_user.user_id

    async def save(self, transaction: Transaction) -> None:
        # Check if transaction already exists
        model = await self._find_model_by_id(transaction.id)

        if model:
            # Update existing
            logger.debug("Updating existing transaction: %s", transaction.id)
            await self._update_model_from_domain(model, transaction)
        else:
            # Create new
            logger.debug("Creating new transaction: %s", transaction.description)
            model = await self._create_model_from_domain(transaction)
            self._session.add(model)

        await self._session.flush()
        logger.info(
            "Transaction saved: %s (ID: %s)",
            transaction.description,
            transaction.id,
        )

    async def find_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        model = await self._find_model_by_id(transaction_id)

        if not model:
            return None

        return await self._map_to_domain(model)

    async def find_by_account(self, account_id: UUID) -> List[Transaction]:
        stmt = self._base_user_query()
        stmt = self._apply_account_filter(stmt, account_id)
        return await self._execute_and_map(stmt)

    async def find_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Transaction]:
        stmt = self._base_user_query()
        stmt = self._apply_date_filters(stmt, start_date, end_date)
        stmt = stmt.order_by(TransactionModel.date.desc())
        return await self._execute_and_map(stmt)

    async def find_all(self) -> List[Transaction]:
        stmt = self._base_user_query()
        return await self._execute_and_map(stmt)

    async def find_posted_transactions(self) -> List[Transaction]:
        stmt = self._base_user_query()
        stmt = self._apply_status_filter(stmt, "posted")
        return await self._execute_and_map(stmt)

    async def find_draft_transactions(self) -> List[Transaction]:
        stmt = self._base_user_query()
        stmt = self._apply_status_filter(stmt, "draft")
        return await self._execute_and_map(stmt)

    async def delete(self, transaction_id: UUID) -> None:
        model = await self._find_model_by_id(transaction_id)

        if model:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("Transaction deleted: %s", transaction_id)

    async def find_by_counterparty(self, counterparty: str) -> List[Transaction]:
        stmt = self._base_user_query().where(
            TransactionModel.counterparty == counterparty,
        )
        return await self._execute_and_map(stmt)

    async def find_by_counterparty_iban(
        self,
        counterparty_iban: str,
    ) -> List[Transaction]:
        normalized = normalize_iban(counterparty_iban)
        if not normalized:
            return []

        stmt = self._base_user_query().where(
            TransactionModel.counterparty_iban == normalized,
        )
        return await self._execute_and_map(stmt)

    async def find_by_metadata(
        self,
        metadata_key: str,
        metadata_value: Optional[Any] = None,
    ) -> List[Transaction]:
        # Fetch all user's transactions and filter in Python for database compatibility
        # This avoids PostgreSQL-specific JSONB operators like has_key() and astext
        stmt = select(TransactionModel).where(
            TransactionModel.user_id == self._user_id,
            TransactionModel.transaction_metadata.isnot(None),
        )
        result = await self._session.execute(stmt)
        models = result.unique().scalars().all()

        transactions = []
        for model in models:
            metadata = model.transaction_metadata or {}

            # Check if key exists
            if metadata_key not in metadata:
                continue

            # If value specified, check if it matches
            if metadata_value is not None:
                stored_value = metadata.get(metadata_key)
                # Handle both string and non-string comparisons
                if stored_value != metadata_value and str(stored_value) != str(
                    metadata_value,
                ):
                    continue

            # Map to domain and add to results
            transaction = await self._map_to_domain(model)
            if transaction:
                transactions.append(transaction)

        return transactions

    async def find_by_account_and_counterparty(
        self,
        account_id: UUID,
        counterparty: str,
    ) -> List[Transaction]:
        stmt = self._base_user_query().where(
            TransactionModel.counterparty == counterparty,
        )
        stmt = self._apply_account_filter(stmt, account_id)
        return await self._execute_and_map(stmt)

    async def find_with_filters(  # NOQA: PLR0913
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        account_id: Optional[UUID] = None,
        exclude_internal_transfers: bool = False,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Transaction]:
        # Build base query scoped to user
        stmt = self._base_user_query()

        # Apply filters
        stmt = self._apply_date_filters(stmt, start_date, end_date)
        stmt = self._apply_status_filter(stmt, status)
        stmt = self._apply_account_filter(stmt, account_id)
        stmt = self._apply_transfer_filter(stmt, exclude_internal_transfers)
        stmt = self._apply_source_filter(stmt, source_filter)

        # Finalize query with ordering and limit
        stmt = stmt.order_by(TransactionModel.date.desc())
        if limit:
            stmt = stmt.limit(limit)

        return await self._execute_and_map(stmt)

    def _base_user_query(self):
        return select(TransactionModel).where(
            TransactionModel.user_id == self._user_id,
        )

    def _apply_date_filters(
        self,
        stmt,
        start_date: Optional[str],
        end_date: Optional[str],
    ):
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(TransactionModel.date >= start_dt)

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.where(TransactionModel.date <= end_dt)

        return stmt

    def _apply_status_filter(self, stmt, status: Optional[str]):
        if status == "posted":
            stmt = stmt.where(TransactionModel.is_posted == True)  # NOQA: E712
        elif status == "draft":
            stmt = stmt.where(TransactionModel.is_posted == False)  # NOQA: E712
        return stmt

    def _apply_account_filter(self, stmt, account_id: Optional[UUID]):
        if account_id:
            # Subquery to find transaction IDs that have entries for this account
            subq = (
                select(JournalEntryModel.transaction_id)
                .where(JournalEntryModel.account_id == account_id)
                .distinct()
                .scalar_subquery()
            )
            stmt = stmt.where(TransactionModel.id.in_(subq))
        return stmt

    def _apply_transfer_filter(self, stmt, exclude_internal_transfers: bool):
        if exclude_internal_transfers:
            stmt = stmt.where(TransactionModel.is_internal_transfer == False)  # NOQA: E712
        return stmt

    def _apply_source_filter(self, stmt, source_filter: Optional[str]):
        if source_filter:
            stmt = stmt.where(TransactionModel.source == source_filter)
        return stmt

    async def _execute_and_map(self, stmt) -> List[Transaction]:
        result = await self._session.execute(stmt)
        models = result.unique().scalars().all()

        transactions = []
        for model in models:
            transaction = await self._map_to_domain(model)
            if transaction:
                transactions.append(transaction)

        return transactions

    async def count_by_status(self) -> dict[str, int]:
        # Count posted
        posted_stmt = (
            select(func.count())
            .select_from(TransactionModel)
            .where(
                TransactionModel.user_id == self._user_id,
                TransactionModel.is_posted == True,  # NOQA: E712
            )
        )
        posted_result = await self._session.execute(posted_stmt)
        posted_count = posted_result.scalar() or 0

        # Count drafts
        draft_stmt = (
            select(func.count())
            .select_from(TransactionModel)
            .where(
                TransactionModel.user_id == self._user_id,
                TransactionModel.is_posted == False,  # NOQA: E712
            )
        )
        draft_result = await self._session.execute(draft_stmt)
        draft_count = draft_result.scalar() or 0

        return {
            "posted": posted_count,
            "draft": draft_count,
            "total": posted_count + draft_count,
        }

    async def _find_model_by_id(
        self,
        transaction_id: UUID,
    ) -> Optional[TransactionModel]:
        stmt = select(TransactionModel).where(
            TransactionModel.user_id == self._user_id,
            TransactionModel.id == transaction_id,
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def _create_model_from_domain(
        self,
        transaction: Transaction,
    ) -> TransactionModel:
        # Create transaction model
        model = TransactionModel(
            id=transaction.id,
            user_id=transaction.user_id,
            description=transaction.description,
            date=transaction.date,
            counterparty=transaction.counterparty,
            counterparty_iban=transaction.counterparty_iban,
            source=transaction.source.value,
            source_iban=transaction.source_iban,
            is_internal_transfer=transaction.is_internal_transfer,
            transaction_metadata=transaction.metadata_raw,
            is_posted=transaction.is_posted,
            created_at=transaction.created_at,
        )

        # Create journal entry models
        for entry in transaction.entries:
            entry_model = JournalEntryModel(
                id=entry.id,
                transaction_id=transaction.id,
                account_id=entry.account.id,
                debit_amount=entry.debit.amount,
                credit_amount=entry.credit.amount,
                currency=entry.amount.currency.code,
            )
            model.entries.append(entry_model)

        return model

    async def _update_model_from_domain(
        self,
        model: TransactionModel,
        transaction: Transaction,
    ) -> None:
        # Update transaction fields
        model.user_id = transaction.user_id
        model.description = transaction.description
        model.date = transaction.date
        model.counterparty = transaction.counterparty
        model.counterparty_iban = transaction.counterparty_iban
        model.source = transaction.source.value
        model.source_iban = transaction.source_iban
        model.is_internal_transfer = transaction.is_internal_transfer
        model.transaction_metadata = transaction.metadata_raw
        model.is_posted = transaction.is_posted

        # Clear existing entries
        model.entries.clear()

        # Add updated entries
        for entry in transaction.entries:
            entry_model = JournalEntryModel(
                id=entry.id,
                transaction_id=transaction.id,
                account_id=entry.account.id,
                debit_amount=entry.debit.amount,
                credit_amount=entry.credit.amount,
                currency=entry.amount.currency.code,
            )
            model.entries.append(entry_model)

    async def _map_to_domain(self, model: TransactionModel) -> Optional[Transaction]:
        # Reconstruct the transaction
        transaction = Transaction.__new__(Transaction)
        transaction._id = model.id
        transaction._user_id = model.user_id
        transaction._description = model.description
        transaction._date = model.date
        transaction._counterparty = model.counterparty
        transaction._counterparty_iban = model.counterparty_iban
        transaction._source = TransactionSource.from_string(model.source)
        transaction._source_iban = model.source_iban
        transaction._is_internal_transfer = model.is_internal_transfer
        transaction._metadata = (
            model.transaction_metadata.copy() if model.transaction_metadata else {}
        )
        transaction._is_posted = model.is_posted
        transaction._created_at = model.created_at
        transaction._entries = []

        # Reconstruct journal entries with strict validation
        for entry_model in model.entries:
            entry = await self._reconstitute_journal_entry(entry_model)
            if entry is not None:
                transaction._entries.append(entry)

        return transaction

    async def _reconstitute_journal_entry(
        self,
        entry_model: JournalEntryModel,
    ) -> Optional[JournalEntry]:
        # Load account
        account = await self._account_repo.find_by_id(entry_model.account_id)
        if not account:
            logger.warning(
                "DATA INTEGRITY: Account %s not found for entry %s in transaction %s",
                entry_model.account_id,
                entry_model.id,
                entry_model.transaction_id,
            )
            return None

        # Validate XOR constraint: exactly one of debit/credit must be positive
        debit_positive = entry_model.debit_amount > Decimal("0")
        credit_positive = entry_model.credit_amount > Decimal("0")

        if debit_positive and credit_positive:
            logger.error(
                "DATA INTEGRITY VIOLATION: Entry %s has both debit (%s) and "
                "credit (%s) positive. Transaction: %s, Account: %s. "
                "Skipping entry to prevent corruption spread.",
                entry_model.id,
                entry_model.debit_amount,
                entry_model.credit_amount,
                entry_model.transaction_id,
                entry_model.account_id,
            )
            return None

        if not debit_positive and not credit_positive:
            logger.error(
                "DATA INTEGRITY VIOLATION: Entry %s has both debit and credit "
                "as zero. Transaction: %s, Account: %s. "
                "Skipping entry to prevent corruption spread.",
                entry_model.id,
                entry_model.transaction_id,
                entry_model.account_id,
            )
            return None

        # Validate non-negative amounts
        if entry_model.debit_amount < Decimal("0"):
            logger.error(
                "DATA INTEGRITY VIOLATION: Entry %s has negative debit (%s). "
                "Transaction: %s, Account: %s. Skipping entry.",
                entry_model.id,
                entry_model.debit_amount,
                entry_model.transaction_id,
                entry_model.account_id,
            )
            return None

        if entry_model.credit_amount < Decimal("0"):
            logger.error(
                "DATA INTEGRITY VIOLATION: Entry %s has negative credit (%s). "
                "Transaction: %s, Account: %s. Skipping entry.",
                entry_model.id,
                entry_model.credit_amount,
                entry_model.transaction_id,
                entry_model.account_id,
            )
            return None

        # Reconstruct journal entry (validation passed)
        entry = JournalEntry.__new__(JournalEntry)
        entry._id = entry_model.id
        entry._account = account

        currency = Currency(entry_model.currency)
        zero_amount = Money(Decimal("0"), currency)

        if debit_positive:
            entry._debit = Money(entry_model.debit_amount, currency)
            entry._credit = zero_amount
        else:
            entry._debit = zero_amount
            entry._credit = Money(entry_model.credit_amount, currency)

        return entry
