"""SQLAlchemy implementation of BankTransactionRepository."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.banking.repositories import (
    BankTransactionRepository,
    StoredBankTransaction,
)
from swen.domain.banking.value_objects import BankTransaction
from swen.infrastructure.persistence.sqlalchemy.models import (
    BankAccountModel,
    BankTransactionModel,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser

logger = logging.getLogger(__name__)


class BankTransactionRepositorySQLAlchemy(BankTransactionRepository):
    """SQLAlchemy implementation of bank transaction repository.

    Uses hash + sequence deduplication strategy to handle identical transactions.
    """

    def __init__(self, session: AsyncSession, current_user: CurrentUser):
        self._session = session
        self._current_user = current_user

    async def save(self, transaction: BankTransaction, account_iban: str) -> UUID:
        results = await self.save_batch_with_deduplication([transaction], account_iban)
        return results[0].id

    async def save_batch(
        self,
        transactions: list[BankTransaction],
        account_iban: str,
    ) -> list[UUID]:
        results = await self.save_batch_with_deduplication(transactions, account_iban)
        return [r.id for r in results]

    async def save_batch_with_deduplication(
        self,
        transactions: list[BankTransaction],
        account_iban: str,
    ) -> list[StoredBankTransaction]:
        if not transactions:
            return []

        # Get account
        account = await self._get_account_by_iban(account_iban)
        if not account:
            msg = f"Account with IBAN {account_iban} not found"
            raise ValueError(msg)

        # Step 1: Compute hashes and assign sequence numbers within the batch
        hash_sequences: dict[str, int] = defaultdict(int)
        tx_with_sequences: list[tuple[BankTransaction, str, int]] = []

        for tx in transactions:
            identity_hash = tx.compute_identity_hash(account_iban)
            seq = hash_sequences[identity_hash] + 1
            hash_sequences[identity_hash] = seq
            tx_with_sequences.append((tx, identity_hash, seq))

        # Step 2: Check which (hash, sequence) combinations already exist
        existing_map = await self._get_existing_by_hash_sequences(
            account.id,
            [(h, s) for _, h, s in tx_with_sequences],
        )

        # Step 3: Process each transaction
        results: list[StoredBankTransaction] = []
        new_models: list[BankTransactionModel] = []

        for tx, identity_hash, seq in tx_with_sequences:
            key = (identity_hash, seq)

            if key in existing_map:
                # Already exists - return existing record
                existing_model = existing_map[key]
                results.append(
                    StoredBankTransaction(
                        id=existing_model.id,
                        identity_hash=identity_hash,
                        hash_sequence=seq,
                        transaction=tx,
                        is_imported=existing_model.is_imported,
                        is_new=False,
                    ),
                )
            else:
                # New transaction - create model
                model = self._create_model_from_domain(
                    tx,
                    account.id,
                    identity_hash,
                    seq,
                )
                new_models.append(model)
                results.append(
                    StoredBankTransaction(
                        id=model.id,
                        identity_hash=identity_hash,
                        hash_sequence=seq,
                        transaction=tx,
                        is_imported=False,
                        is_new=True,
                    ),
                )

        # Step 4: Save new models
        if new_models:
            self._session.add_all(new_models)
            await self._session.flush()
            logger.info(
                "Saved %d new bank transaction(s) for account %s",
                len(new_models),
                account_iban,
            )

        skipped = len(transactions) - len(new_models)
        if skipped > 0:
            logger.info(
                "Skipped %d existing bank transaction(s) for account %s",
                skipped,
                account_iban,
            )

        return results

    async def find_unimported(self, account_iban: str) -> list[StoredBankTransaction]:
        account = await self._get_account_by_iban(account_iban)
        if not account:
            return []

        stmt = (
            select(BankTransactionModel)
            .where(
                and_(
                    BankTransactionModel.account_id == account.id,
                    BankTransactionModel.is_imported == False,  # noqa: E712
                ),
            )
            .order_by(
                BankTransactionModel.booking_date,
                BankTransactionModel.identity_hash,
                BankTransactionModel.hash_sequence,
            )
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [
            StoredBankTransaction(
                id=m.id,
                identity_hash=m.identity_hash,
                hash_sequence=m.hash_sequence,
                transaction=self._map_to_domain(m),
                is_imported=m.is_imported,
                is_new=False,
            )
            for m in models
        ]

    async def mark_as_imported(self, transaction_id: UUID) -> None:
        stmt = select(BankTransactionModel).where(
            BankTransactionModel.id == transaction_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.is_imported = True
            await self._session.flush()

    async def find_by_id(self, transaction_id: UUID) -> Optional[BankTransaction]:
        stmt = select(BankTransactionModel).where(
            BankTransactionModel.id == transaction_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._map_to_domain(model)

    async def find_by_account(
        self,
        account_iban: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BankTransaction]:
        # Get account
        account = await self._get_account_by_iban(account_iban)
        if not account:
            return []

        # Build query
        stmt = select(BankTransactionModel).where(
            BankTransactionModel.account_id == account.id,
        )

        if start_date:
            stmt = stmt.where(BankTransactionModel.booking_date >= start_date)

        if end_date:
            stmt = stmt.where(BankTransactionModel.booking_date <= end_date)

        # Order by date descending (most recent first)
        stmt = stmt.order_by(BankTransactionModel.booking_date.desc())

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._map_to_domain(model) for model in models]

    async def exists(self, account_iban: str, bank_reference: str) -> bool:
        # Get account
        account = await self._get_account_by_iban(account_iban)
        if not account:
            return False

        stmt = select(BankTransactionModel.id).where(
            and_(
                BankTransactionModel.account_id == account.id,
                BankTransactionModel.bank_reference == bank_reference,
            ),
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_latest_transaction_date(
        self,
        account_iban: str,
    ) -> Optional[date]:
        # Get account
        account = await self._get_account_by_iban(account_iban)
        if not account:
            return None

        stmt = select(func.max(BankTransactionModel.booking_date)).where(
            BankTransactionModel.account_id == account.id,
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_account(self, account_iban: str) -> int:
        # Get account
        account = await self._get_account_by_iban(account_iban)
        if not account:
            return 0

        stmt = select(func.count(BankTransactionModel.id)).where(
            BankTransactionModel.account_id == account.id,
        )

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def _get_account_by_iban(self, iban: str) -> Optional[BankAccountModel]:
        stmt = select(BankAccountModel).where(
            and_(
                BankAccountModel.iban == iban,
                BankAccountModel.user_id == self._current_user.user_id,
            ),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_existing_by_hash_sequences(
        self,
        account_id: int,
        hash_sequences: list[tuple[str, int]],
    ) -> dict[tuple[str, int], BankTransactionModel]:
        if not hash_sequences:
            return {}

        # Get unique hashes
        unique_hashes = list({h for h, _ in hash_sequences})

        # Query all transactions with these hashes
        stmt = select(BankTransactionModel).where(
            and_(
                BankTransactionModel.account_id == account_id,
                BankTransactionModel.identity_hash.in_(unique_hashes),
            ),
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        # Build lookup map
        existing_map: dict[tuple[str, int], BankTransactionModel] = {}
        for model in models:
            key = (model.identity_hash, model.hash_sequence)
            existing_map[key] = model

        return existing_map

    def _create_model_from_domain(
        self,
        transaction: BankTransaction,
        account_id: int,
        identity_hash: str,
        hash_sequence: int,
    ) -> BankTransactionModel:
        return BankTransactionModel(
            id=uuid4(),  # Random UUID - uniqueness is via hash+sequence
            account_id=account_id,
            identity_hash=identity_hash,
            hash_sequence=hash_sequence,
            booking_date=transaction.booking_date,
            value_date=transaction.value_date,
            amount=transaction.amount,
            currency=transaction.currency,
            purpose=transaction.purpose,
            applicant_name=transaction.applicant_name,
            applicant_iban=transaction.applicant_iban,
            applicant_bic=transaction.applicant_bic,
            bank_reference=transaction.bank_reference,
            customer_reference=transaction.customer_reference,
            end_to_end_reference=transaction.end_to_end_reference,
            mandate_reference=transaction.mandate_reference,
            creditor_id=transaction.creditor_id,
            transaction_code=transaction.transaction_code,
            posting_text=transaction.posting_text,
            is_imported=False,
        )

    def _map_to_domain(self, model: BankTransactionModel) -> BankTransaction:
        return BankTransaction(
            booking_date=model.booking_date,
            value_date=model.value_date,
            amount=model.amount,
            currency=model.currency,
            purpose=model.purpose,
            applicant_name=model.applicant_name,
            applicant_iban=model.applicant_iban,
            applicant_bic=model.applicant_bic,
            bank_reference=model.bank_reference,
            customer_reference=model.customer_reference,
            end_to_end_reference=model.end_to_end_reference,
            mandate_reference=model.mandate_reference,
            creditor_id=model.creditor_id,
            transaction_code=model.transaction_code,
            posting_text=model.posting_text,
        )
