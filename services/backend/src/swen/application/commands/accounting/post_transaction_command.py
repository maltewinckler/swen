"""Commands to post and unpost accounting transactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.application.services.ml_example_service import MLExampleService
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.exceptions import (
    TransactionAlreadyDraftError,
    TransactionAlreadyPostedError,
    TransactionNotFoundError,
)
from swen.domain.accounting.repositories import TransactionRepository
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.ml_service import MLServicePort

logger = logging.getLogger(__name__)


class PostTransactionCommand:
    """Post a draft transaction."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        ml_port: MLServicePort | None = None,
    ):
        self._transaction_repo = transaction_repository
        self._ml_example_service = MLExampleService(ml_port)

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_port: MLServicePort | None = None,
    ) -> PostTransactionCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            ml_port=ml_port,
        )

    async def execute(self, transaction_id: UUID) -> Transaction:
        transaction = await self._transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError(transaction_id)

        if transaction.is_posted:
            raise TransactionAlreadyPostedError(transaction_id)

        transaction.post()
        await self._transaction_repo.save(transaction)

        # Submit as training example (fire-and-forget)
        self._ml_example_service.submit_example(transaction)

        return transaction


class UnpostTransactionCommand:
    """Revert a posted transaction to draft."""

    def __init__(self, transaction_repository: TransactionRepository):
        self._transaction_repo = transaction_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UnpostTransactionCommand:
        return cls(transaction_repository=factory.transaction_repository())

    async def execute(self, transaction_id: UUID) -> Transaction:
        transaction = await self._transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError(transaction_id)

        if not transaction.is_posted:
            raise TransactionAlreadyDraftError(transaction_id)

        transaction.unpost()
        await self._transaction_repo.save(transaction)

        return transaction


class BulkPostTransactionsCommand:
    """Post multiple draft transactions."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        ml_port: MLServicePort | None = None,
    ):
        self._transaction_repo = transaction_repository
        self._ml_example_service = MLExampleService(ml_port)

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_port: MLServicePort | None = None,
    ) -> BulkPostTransactionsCommand:
        return cls(
            transaction_repository=factory.transaction_repository(),
            ml_port=ml_port,
        )

    async def execute(
        self,
        transaction_ids: list[UUID] | None = None,
        post_all_drafts: bool = False,
    ) -> list[Transaction]:
        if not transaction_ids and not post_all_drafts:
            msg = "Either specify transaction_ids or set post_all_drafts=True"
            raise ValidationError(msg)

        posted = []

        if post_all_drafts:
            drafts = await self._transaction_repo.find_draft_transactions()
            for txn in drafts:
                txn.post()
                await self._transaction_repo.save(txn)
                self._ml_example_service.submit_example(txn)
                posted.append(txn)
        elif transaction_ids:
            for txn_id in transaction_ids:
                txn = await self._transaction_repo.find_by_id(txn_id)
                if txn and not txn.is_posted:
                    txn.post()
                    await self._transaction_repo.save(txn)
                    self._ml_example_service.submit_example(txn)
                    posted.append(txn)

        return posted
