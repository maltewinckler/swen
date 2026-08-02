"""Commands to post and unpost accounting transactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.accounting.dtos.transactions_dto import TransactionDTO
from swen.application.integration.services.ml_example_service import MLExampleService
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.accounting.exceptions import (
    TransactionAlreadyDraftError,
    TransactionAlreadyPostedError,
    TransactionNotFoundError,
)
from swen.domain.accounting.repositories import TransactionRepository
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.account_classifier_training import (
        AccountClassifierTrainingPort,
    )

logger = logging.getLogger(__name__)


class PostTransactionCommand:
    """Post a draft transaction."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        uow: UnitOfWork,
        ml_port: AccountClassifierTrainingPort | None = None,
    ):
        self._transaction_repo = transaction_repository
        self._uow = uow
        self._ml_example_service = MLExampleService(ml_port)

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_port: AccountClassifierTrainingPort | None = None,
    ) -> PostTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            uow=factory.unit_of_work(),
            ml_port=ml_port,
        )

    async def execute(self, transaction_id: UUID) -> TransactionDTO:
        async with self._uow:
            transaction = await self._transaction_repo.find_by_id(transaction_id)
            if not transaction:
                raise TransactionNotFoundError(transaction_id)

            if transaction.is_posted:
                raise TransactionAlreadyPostedError(transaction_id)

            transaction.post()
            await self._transaction_repo.save(transaction)

        # Submit as training example (fire-and-forget)
        self._ml_example_service.submit_example(transaction)

        return TransactionDTO.from_transaction(transaction)


class UnpostTransactionCommand:
    """Revert a posted transaction to draft."""

    def __init__(self, transaction_repository: TransactionRepository, uow: UnitOfWork):
        self._transaction_repo = transaction_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UnpostTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, transaction_id: UUID) -> TransactionDTO:
        async with self._uow:
            transaction = await self._transaction_repo.find_by_id(transaction_id)
            if not transaction:
                raise TransactionNotFoundError(transaction_id)

            if not transaction.is_posted:
                raise TransactionAlreadyDraftError(transaction_id)

            transaction.unpost()
            await self._transaction_repo.save(transaction)

            return TransactionDTO.from_transaction(transaction)


class BulkPostTransactionsCommand:
    """Post multiple draft transactions."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        uow: UnitOfWork,
        ml_port: AccountClassifierTrainingPort | None = None,
    ):
        self._transaction_repo = transaction_repository
        self._uow = uow
        self._ml_example_service = MLExampleService(ml_port)

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_port: AccountClassifierTrainingPort | None = None,
    ) -> BulkPostTransactionsCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            uow=factory.unit_of_work(),
            ml_port=ml_port,
        )

    async def execute(
        self,
        transaction_ids: list[UUID] | None = None,
        post_all_drafts: bool = False,
    ) -> list[TransactionDTO]:
        if not transaction_ids and not post_all_drafts:
            msg = "Either specify transaction_ids or set post_all_drafts=True"
            raise ValidationError(msg)

        posted = []

        async with self._uow:
            if post_all_drafts:
                drafts = await self._transaction_repo.find_draft_transactions()
                for txn in drafts:
                    txn.post()
                    await self._transaction_repo.save(txn)
                    posted.append(txn)
            elif transaction_ids:
                for txn_id in transaction_ids:
                    txn = await self._transaction_repo.find_by_id(txn_id)
                    if txn and not txn.is_posted:
                        txn.post()
                        await self._transaction_repo.save(txn)
                        posted.append(txn)

        # Submit as training examples (fire-and-forget), after commit
        for txn in posted:
            self._ml_example_service.submit_example(txn)

        return [TransactionDTO.from_transaction(txn) for txn in posted]
